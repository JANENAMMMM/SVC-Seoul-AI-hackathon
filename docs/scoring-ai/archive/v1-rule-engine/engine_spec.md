# ScoringAI 산정 엔진 명세 v1.0

> 원칙: **판단은 규칙, 근거는 측정값 우선.** LLM은 등급을 정하지 않는다.
> 입력: `data/scoring/derived/*.json` → 정규화 `data/scoring/features.json` → 등급 `data/scoring/grades.json`

## 1. 근거 등급 (출처 신뢰도)

| 등급 | 출처 | 예 |
|---|---|---|
| A | 실측 행동 데이터 | OSM 공개 GPS 궤적 (궤적 5개 이상) |
| B | 지도·지형·공식 사실 | OSM 보행로·계단·케이블카 태그, 고도 데이터, 운영사·정부 공식 정보 |
| C | 리뷰 집계 | Tripadvisor 언급률(표본 ≥100), Google topics 언급 수 |

- 차원마다 **가장 높은 등급의 근거**로 수준을 정하고, 낮은 등급은 "일치/불일치" 확인에만 쓴다
- 근거 간 수준이 2단계 이상 다르면 `needs_review`
- C 등급만 있는 차원은 `evidence: "weak"` 표시

## 2. 차원과 수준 (하=0, 중=1, 상=2)

| 차원 | A 근거 | B 근거 | C 근거 | 하 / 중 / 상 기준 (팀 가정값) |
|---|---|---|---|---|
| D1 보행 거리 | GPS 궤적 보행 km 중앙값 | OSM 부지 내 보행로 길이(km)·부지 면적 | 리뷰 걷기 언급률 | km: <1 / 1~3 / ≥3 · 언급률: <10% / 10~25% / ≥25% |
| D2 피할 수 없는 오르막·계단 | GPS 궤적 상승 중앙값(m) | 도보 구간 상승(m, 케이블카 제외), 계단 수, 공식 "계단 필수" | 리뷰 계단 언급률 | 상승 m: <15 / 15~60 / ≥60 · 계단 수: <50 / 50~200 / ≥200 · 언급률: <10% / 10~30% / ≥30% |
| D3 대체 이동수단 | — | 케이블카·엘리베이터·셔틀·전기카트 유무와 범위 | 리뷰 완화 언급률 | 있음/없음 (보정 요소) |
| D4 더위 노출 | — | 실외 비율(공식·유형) × 방문 월 체감 최고기온 | 리뷰 더위 언급률 | 실내 / 실외·체감<32℃ / 실외·체감≥32℃ |
| D5 대기·혼잡 | — | — | 리뷰 혼잡 언급률, Google `crowded` 언급 비율 | 언급률: <15% / 15~30% / ≥30% |

- 수치 기준은 **팀 가정값**: 50대 이상 보행 속도 약 0.8 m/s(1 km ≈ 21분 연속 보행), 계단 오르기 4.5~6.8 MET vs 평지 2.3~3.5 MET(2024 Compendium), UTCI 강한 열스트레스 32℃(UTCI 구간), 호주 보행로 등급의 "계단·경사 → 상위 등급" 논리
- 오탐 보정: 온천의 "hot spring/hot water", 해변의 "sand"는 각 차원 언급에서 제외

## 3. 종합 등급 규칙

```
base   = max(D1, D2)
if D2 == 상 and D3 == 없음:  grade = 상  (강제)
else:
    if D3 == 있음 and D3가 주요 오르막 구간을 대신함:  D2 -= 1 후 base 재계산
    grade = base
    if D4 == 상 and D2 >= 중:  grade += 1   # 더위 보정: 더운 실외에서 오르막(고 MET)일 때만 (v1.0.1)
    elif D4 == 상:  flag "heat_flag_low_exertion"  # 평지 보행은 표시만
    if D5 == 상 and grade < 상:  grade += 1 ... 단 D5는 C 근거뿐이므로 'flag_only' 옵션으로 끌 수 있음
grade = clamp(grade, 하, 상)
```

- 출력에 **어떤 규칙이 적용됐는지**(`rules_fired`)와 차원별 사용 근거·값을 모두 남긴다
- 시기 인자 `visit_month`(기본 7월)로 D4를 다시 계산할 수 있어야 한다

## 4. 출력 (`grades.json`, 관광지별)

```json
{
  "id": "dad-02", "name_ko": "오행산(마블마운틴)", "grade": "상", "grade_score": 2,
  "dimensions": {
    "D1": {"level": 1, "basis": "A", "value": 1.70, "unit": "km", "source": "gps_traces"},
    "D2": {"level": 2, "basis": "B", "value": 156, "unit": "steps", "source": "site_facts",
           "checks": [{"basis": "C", "value": 0.61, "level": 2, "agree": true}]}
  },
  "rules_fired": ["D2_high_no_full_relief", "heat_plus_1"],
  "status": "draft | needs_review", "review_reasons": [],
  "rubric_version": "1.0", "visit_month": 7
}
```

## 5. 검증 (`docs/scoring-ai/validation_report.md`)

- 차원별 결측률, 근거 등급 분포
- A·B 근거 수준과 C(리뷰) 수준의 일치율·스피어만 상관
- 민감도: 모든 기준값 ±20% 변경 시 등급이 바뀌는 관광지 수
- 종합 등급표 15곳
