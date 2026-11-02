# 대안 객관 지표 조사 (관광지 내부 보행 부담)

목표: "방문객이 관광지 안에서 실제로 얼마나, 얼마나 힘들게 걷는가"를 공개 데이터로 측정.
프로토타입: `src/scoring/collect/alt_probe.py`, 추출값: `data/scoring/derived/site_facts.json`

## 1. OSM 공개 GPS trace (trackpoints API) — 추천 1순위(보조 지표)
- API: `/api/0.6/trackpoints?bbox=...` (ODbL, 공개 API, UA 명시·저빈도 호출이면 이용 약관상 문제 없음)
- 결과(2026-11-02 실측)
  - 마블마운틴(bbox 108.255–108.272, 15.995–16.010): 포인트 21,978개, 트랙 세그먼트 30개,
    타임스탬프 있는 식별 trace 13개. 구간 거리 0.65–2.9km, 중앙값 약 1.75km.
    예: taki3hira 2.06km / 1h51m, Rick-Rainer Ludwig 2.88km / 2h26m
  - 바나힐(107.975–108.005, 15.985–16.010): 포인트 6,509개, 식별 trace 1개
    (8.86km / 4h10m + 4.49km / 1h06m). 표본이 너무 적음
- 한계: GPX에 ele 값이 없음(climb 계산 불가), 이 경우 DEM(SRTM)을 따로 붙여야 함.
  bbox 안에 차량 이동이나 주변 도로 trace가 섞이므로 속도 6km/h 이하 구간만 필터링해야 함.
  15곳 중 인기 장소(마블마운틴, 호이안 구시가, 미케비치 등)만 표본 5개 이상이 나올 것으로 예상.
- 객관성: 높음(실측 궤적). 실현성: 중간(표본 편차 큼)

## 2. 공식/가이드 사실값(계단 수·엘리베이터 유무) — 추천 1순위(핵심 지표)
- 마블마운틴 Thuy Son: 정상까지 약 156계단, 엘리베이터 있음(편도 15,000 VND, 100–156계단 생략),
  전체 관람 시 약 400계단. 동굴(Huyen Khong)과 정상은 계단만 이용 가능
  - 출처: hoiandaytrip.com/marble-mountains-elevator/, sunparadiseland.com 가이드
- 바나힐: 케이블카로 정상부 접근, 내부는 상당 부분 평지와 계단. 공식 계단 수는 못 찾음
- 객관성: 높음(검증 가능한 수치). 실현성: 높음(장소당 수작업 5분, 15곳이면 1–2시간)
- 지표 예: `steps_count`, `elevator`(0/1), `cable_car_or_shuttle`(0/1), `wheelchair_ok`

## 3. Wikiloc / AllTrails / Komoot
- Wikiloc: 바나힐 '14 parque' 1건(14.8km, gain 1,488m, Easy). 케이블카 고도가 섞여 오염된 값
- AllTrails: 해당 없음. Komoot: 하이라이트 지점만 있고 경로 거리나 상승고는 없음
- 약관: 스크래핑 금지(AllTrails, Komoot), 페이지를 사람이 열람해 사실값 인용하는 것만 가능
- 하이킹형 장소(선짜반도, 하이반 고개)만 쓸 만하고 도시 관광지는 커버리지가 거의 없음
- 객관성: 중간. 실현성: 낮음

## 4. 기타 아이디어
- OSM 내부 보행망 길이 + `highway=steps` 태그 개수/길이(Overpass): 공개, 객관적이고
  15곳 모두 자동화 가능. trace보다 커버리지가 좋다. 다음 단계로 강력 추천
- Wheelmap(OSM `wheelchair=*` 태그): 다낭 지역은 태그가 희박할 것으로 예상, 보조 지표 정도
- YouTube 워킹투어 영상 길이: 편집이나 배속 영향이 커서 객관성 낮음. API 키가 필요
- Strava heatmap: 로그인이 필요하고 약관상 데이터 추출이 금지됨. 사용 불가
- Google Street View 내부 경로 커버리지: 약관상 자동 수집 금지, 수동 확인만 가능

## 순위 (객관성 × 실현성)
1. 계단 수·엘리베이터 등 사실값(수작업) 2. OSM steps/보행망(Overpass)
3. OSM GPS trace(표본 있는 곳만) 4. Wheelmap 5. Wikiloc류 6. YouTube/Strava/Street View(제외)
