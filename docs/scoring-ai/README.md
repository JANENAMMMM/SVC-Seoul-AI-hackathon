# ScoringAI — 관광지 여행 난이도 평가 (최종 문서)

> **이 문서 하나로 ScoringAI의 현재 상태를 파악할 수 있게 정리했다.** 세부는 링크로 연결한다.
> 담당: 남재은 · 브랜치 `JANENAMMMM/scoring-ai` · 기준: 2026-11-03 · 현재 버전 **v2.1**
> 과거 변경 이력: [CHANGELOG.md](CHANGELOG.md)

---

## 1. 한 줄 요약

다낭권 관광지 15곳의 **여행 난이도를 1~10점 + 관람 방식별 점수**로 매기고, 점수마다 **근거(출처 ID·URL)** 를 붙인다. 상품 일정을 넣으면 **일차별·패키지 난이도**와 "관람 방식을 바꾸면 몇 점으로 내려가는지"를 계산한다.

## 2. 왜 이렇게 만들었나 (설계 원칙 3개)

| 원칙 | 내용 | 이유 |
|---|---|---|
| 근거는 DB에 | 지도·GPS·공식 사실·리뷰·기후를 출처와 한계 메모까지 저장 | 멘토 지적: "그 정보를 어디서 구하나" |
| 해석은 LLM judge, 합산은 코드 | Claude가 도구로 근거를 조회·웹 검색해 차원 점수를 내고, 종합 점수는 코드가 가중평균 | 관광지 범위·실제 관람 경로(정상까지 안 갈 수 있음, 케이블카가 대신함)는 규칙으로 판단 불가 |
| 인용 없으면 무효 | 인용한 근거 ID가 DB에 없거나 수치가 다르면 그 차원은 무효, 3회 실행 중앙값 | LLM끼리도 등급이 8/15만 일치 → 흔들림 억제 장치 필요 |

## 3. 구조

```
수집(src/scoring/collect)  ─▶  근거 DB  Supabase scoring_* 6개 테이블
  Google 식별·주제, Tripadvisor 리뷰,      places 15 · evidence 523 · reviews 1,994
  GPS 궤적, 공식 사실, 기후, OSM(부분)      web_cache · judgments · scores
                                  │ 도구 호출
                                  ▼
                 LLM judge (Claude Sonnet, rubric v2.1)
                 get_place · list_evidence · search_reviews · get_climate · web_search · google_web_search
                 ① 대표 관람 경로 → ② 차원별 typical/lower/upper + 조건 + 근거 ID
                                  │
                                  ▼
                 검증 코드: 인용 실재·수치 일치, 3회 중앙값, 폭 >2 → needs_review
                                  │
                                  ▼
       점수(scores_v2.json) ─▶ 관람 방식 카탈로그(visit_modes_v2_1.json) ─▶ 패키지 난이도 · API
```

- 상세 명세: [judge_spec_v2.md](spec/judge_spec_v2.md) · 근거·일정 연결 규칙: [evidence_workflow.md](spec/evidence_workflow.md)

## 4. 점수 체계

- **차원 4개** (각 1~10, 높을수록 힘듦): 계단·오르막(climb) / 보행량(walking) / 더위(heat) / 혼잡(crowd)
- **종합** = climb 3 · walking 3 · heat 2 · crowd 1 가중평균 (코드 계산). 표시 등급 1~3 하 · 4~6 중 · 7~10 상
- **차원별 앵커**: climb 박물관 1~2 / 호이안 1 / 오행산 정상 8 · walking 2 / 5 / 6 · heat 2 / 7 / 7 · crowd 리뷰 혼잡 20%대 = 5
- **관람 방식 3개**: `standard`(일반) · `short`(이동 보조·짧은 관람) · `full`(전체 관람). climb·walking에 lower/upper 조건을 적용하고 heat·crowd는 typical 유지 → [visit_modes_package.md](spec/visit_modes_package.md)

## 5. 결과 (15곳)

| 관광지 | 종합(일반/하한/상한) | 등급 | 상태 | | 관광지 | 종합 | 등급 | 상태 |
|---|---|---|---|---|---|---|---|---|
| 오행산 | 7 / 4 / 8 | 상 | ok | | 미케 해변 | 3 / 2 / 5 | 하 | ok |
| 바나힐 | 6 / 4 / 8 | 중 | ok | | 아시아파크 | 3 / 2 / 5 | 하 | ok |
| 누이탄타이 온천 | 5 / 3 / 6 | 중 | ok | | 하이반 고개 | 3 / 2 / 5 | 하 | ok |
| 미선 유적지 | 5 / 3 / 6 | 중 | ok | | 호이안 야시장 | 3 / 3 / 5 | 하 | ok |
| 호이안 구시가지 | 4 / 3 / 5 | 중 | ok | | 껌탄 코코넛 마을 | 3 / 2 / 5 | 하 | 검수 대기 |
| 영흥사 | 4 / 3 / 5 | 중 | ok | | 용다리 | 2 / 1 / 4 | 하 | ok |
| 한시장 | 4 / 2 / 5 | 중 | ok | | 다낭 대성당 | 2 / 2 / 4 | 하 | ok |
| | | | | | 참 조각 박물관 | 2 / 1 / 3 | 하 | 검수 대기 |

- 원본: [`data/scoring/scores_v2.json`](../../data/scoring/scores_v2.json) · 관람 방식: [visit_modes_v2_1.json](../../data/scoring/visit_modes_v2_1.json)
- 예: 오행산 `short` = 엘리베이터 이용·사원 일부 → 5점 / `full` = 계단으로 정상까지 → 7점

## 6. 패키지 난이도 (상품기획자용)

- 하루 난이도 = 그날 최고 관광지 점수 + **6점 이상 방문이 연속한 쌍마다 +1**(하루 최대 +2, 상한 10)
- 패키지 결과 = 일차별 점수, 최고(`peak`), 평균(`mean`), 사용한 일정표 근거, 검수 대기 관광지
- 예시: 1일차 바나힐(6) → 오행산 전체(7) = **8점**. 오행산을 `short`(5)로 바꾸면 **6점**
- 일정 입력에는 `place_id`, `mode`, `source_ref`(일정표 쪽·행), `route_note`가 필수. 관람 방식은 자동 추정하지 않음
- 연속 가산은 방문 순서 기준의 **시뮬레이션 규칙**(실제 휴식·이동 시간 미반영)

## 7. 사용 방법

```bash
uv run pytest -q                                              # 테스트 30개
uv run python -m src.scoring.run_judge --sites dad-02 --runs 3 --replace   # 재채점(비용 발생, 기존 점수 덮어쓰기는 --replace 필요)
uv run python -m src.scoring.run_itinerary <일정.json> --output <결과.json>  # 패키지 난이도
uv run python -m src.scoring.run_review_validation docs/scoring-ai/validation/heldout_review_annotations.csv --output <보고서.json>
```

**API** (`api/scoring.py`, 저장된 v2.1 카탈로그를 읽음, DB 쓰기·API 비용 없음)

| 엔드포인트 | 내용 |
|---|---|
| `GET /api/scoring/places` | 15곳 목록·방식별 점수 |
| `GET /api/scoring/places/{place_id}` | 차원 점수·근거 ID·조건 |
| `POST /api/scoring/packages/evaluate` | 일정 JSON → 일차별·패키지 난이도 |

**다른 담당이 쓰는 법**: 동선 짜기 = 방식별 점수와 패키지 함수 · 챗봇 = 조건·근거 ID로 "왜 힘든지" 설명 · UI = 점수, 힘든 이유 1~2개, 부담을 줄이는 조건, 출처 링크, 검수 상태만 노출

## 8. 검증 현황

| 검증 | 결과 | 문서 |
|---|---|---|
| 인용 검증 | 재실행 18/18 통과, 최종 13곳 ok · 2곳 검수 대기 | [CHANGELOG](CHANGELOG.md) |
| v1 규칙 엔진과 비교 | 13곳 중 8곳 등급 일치. 차이는 v2가 웹 검색으로 근거를 보강한 경우(영흥사 계단, 누이탄타이 경사) | [judge_comparison.md](archive/v1-rule-engine/judge_comparison.md) |
| 공개 후기 반례 탐색 | 오행산·바나힐·미선 방식별 차이는 후기와 일치. **참 조각 박물관 더위(냉방 부재), 용다리 쇼·야시장 혼잡은 과소 평가 가능 → 재검토 우선** | [review_spotcheck_2026-11-03.md](validation/review_spotcheck_2026-11-03.md) |
| 채점 미사용 후기 대조 | 양식·스크립트 준비, 작성 전 | [heldout_review_annotations.csv](validation/heldout_review_annotations.csv) |
| 사람 기준셋 | 양식 준비, 작성 전 (팀원 2명 × 30분) | [gold_set_template.md](validation/gold_set_template.md) |

> **주의**: 현재 점수는 "보통 체력 50세 이상"을 가정한 **설계 점수**이며, 실제 고객 체감으로 검증된 값은 아니다. 출시 전 가이드·상품기획자가 AI 점수를 보지 않고 10~15곳을 평가해 ±1점 일치율을 공개해야 설득력이 생긴다.

## 9. 데이터 출처와 한계

| 출처 | 확보 | 해커톤 | 하나투어 운영 |
|---|---|---|---|
| Google Places 공식 | 15곳 식별, 리뷰 주제 언급 수 | O | O (리뷰는 장소당 5건 한계) |
| SerpApi | 식별·주제, Google 웹 검색 도구 | △ | X (비공식) |
| Tripadvisor (Apify) | 13곳 × 150건 | △ 시연용 | X |
| OSM 공개 GPS 궤적 | 실보행 3곳 | O | O |
| 공식 사실·기후 | 15곳 대체수단·실내외, 다낭 월별 체감온도 | O | O |
| 하나투어 자체 후기·가이드 | — | — | **최우선** |

- 법적 검토·출처별 판단: [design_b_serpapi.md §1-6](archive/v0-design/design_b_serpapi.md) · 데이터 조사 보고서: [research/report_data_sources.md](research/report_data_sources.md)
- Google 리뷰 대량 수집은 불가(2026-02 비로그인 제한 보기, SerpApi 미해결 이슈, 자동화 브라우저 로그인 차단)

## 10. 남은 일

1. **재검토 우선 3곳**: 참 조각 박물관 더위, 용다리(쇼 관람 방식 분리), 호이안 야시장 혼잡
2. **사람 검증**: 사람 기준셋 + 채점 미사용 후기 대조 → ±1점 일치율
3. **하나투어 일정표 연결**: 공개 상품 2~3개를 `itin:` 근거로 넣고 일정 기준 점수 산출
4. 정리: 미커밋 변경 커밋, `osm_features.json`(중단된 4곳 측정) 폐기 여부 결정, main 병합 PR

## 11. 파일 지도

| 구분 | 위치 |
|---|---|
| 판정 | `src/scoring/judge.py`, `verify.py`, `run_judge.py`, `provenance.py`, `google_web_search.py` |
| DB·근거 | `src/scoring/db.py`, `load_evidence.py` |
| 관람 방식·패키지 | `src/scoring/visit_modes.py`, `package_difficulty.py`, `itinerary.py`, `run_itinerary.py` |
| 후기 검증 | `src/scoring/review_validation.py`, `run_review_validation.py` |
| v1 규칙 엔진 (기준선) | `src/scoring/engine.py`, `features.py`, `validate.py` · [engine_spec.md](archive/v1-rule-engine/engine_spec.md) |
| 수집 | `src/scoring/collect/` (GPS, OSM, 대안 지표) |
| API | `api/scoring.py` |
| 데이터 | `data/scoring/` (derived 수집 결과, judge 실행 기록, scores_v2.json) |
| 지난 문서 (참고용) | [archive/](archive/README.md) — v0 설계안, v1 규칙 엔진, 작업 로그 |
