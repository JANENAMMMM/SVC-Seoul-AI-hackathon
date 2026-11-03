# ScoringAI 변경 이력

> 최종 상태는 [README.md](README.md). 이 파일은 "무엇을 왜 바꿨는지"의 기록이다. 작업 중 상세 판단 로그는 [orchestration_log.md](archive/worklog/orchestration_log.md).

## v2.1 후속 (2026-11-03, Codex) — 관람 방식·패키지·검증 도구 · 미커밋

- **관람 방식 카탈로그** `visit_modes_v2_1.json`: 15곳 × 3방식(standard/short/full). 차원별 최종 점수 3개와 모두 일치하고 인용 검증을 통과한 실행에서 조건·근거 ID를 가져옴 (없으면 생성 실패) → [visit_modes_package.md](spec/visit_modes_package.md)
- **패키지 난이도** `package_difficulty.py`, `itinerary.py`, `run_itinerary.py`: 하루 최고 점수 + 6점 이상 연속 방문 쌍마다 +1(최대 +2). 일정 입력에 `source_ref`·`route_note` 필수
- **API** `api/scoring.py`: `/api/scoring/places`, `/places/{id}`, `/packages/evaluate` (`api/main.py`에 연결)
- **출처 추적·후기 검증** `provenance.py`, `review_validation.py`, `run_review_validation.py`, 양식 `heldout_review_annotations.csv`. 차원·방식별 표본 3건 미만은 `insufficient`
- **Google 웹 검색 도구** `google_web_search.py`: SerpApi 기반 organic result를 judge 도구로 추가 (Google 공식 API 아님). 연결 확인 1회
- **재채점 안전장치**: `run_judge --replace` 없이는 공개 점수를 덮어쓰지 않음
- **공개 후기 반례 탐색** [review_spotcheck_2026-11-03.md](validation/review_spotcheck_2026-11-03.md): 참 조각 박물관 더위, 용다리 쇼·야시장 혼잡을 과소 평가 가능 지점으로 발견
- 테스트 18 → 30개

## v2.1 (2026-11-03) — 15곳 × 3회 확정 · beface3

- **차원별 앵커로 변경**: 종합 기준 앵커는 코드 합산과 모순(시험에서 앵커보다 1점씩 낮게 나옴) → climb·walking·heat·crowd 각각 앵커
- 핵심 물리 사실이 DB에 없으면 웹 검색 후 채점하도록 지시 → 웹 검색 31회 사용
- **실패 수정**: 45회 중 9회 인용 검증 실패. 원인 ① 점수를 `dimensions` 밖에 둔 출력 형식 이탈 → 1회 재제출 요청 ② 같은 URL의 `www.` 표기 차이 → URL 정규화. 6곳 재실행 18/18 통과
- 결과 파일 덮어쓰기 버그 수정(배치별 병합). 총 비용 약 $9

## v2.0 (2026-11-03) — 근거 DB + 도구 호출 LLM judge · 765d34b

- **전환 이유**: 사용자 피드백 "관광지 범위를 못 잡는데 고도차 계산이 이상하다, 정상까지 안 갈 수도 있다"
- Supabase `scoring_*` 6개 테이블(기존 `hello_world_test` 미접촉), 근거 523·리뷰 1,994건 이관
- 점수 형식을 상·중·하 → **1~10 + 하한·상한(조건·근거 필수)** 으로 변경 (사용자 제안: 하한으로 계산하는 최적화 가능)
- 인용 검증 코드(근거 ID 실재·수치 일치), 시험 2곳 통과 → [v2_trial.md](archive/worklog/v2_trial.md)

## v1.0 (2026-11-02 밤) — 규칙 엔진 · 2d419f7 ~ bb5febe

- 근거 등급 A(GPS)·B(지도·공식)·C(리뷰), 차원 5개, 규칙 판정 → [engine_spec.md](archive/v1-rule-engine/engine_spec.md)
- 더위 보정이 실외 관광지 전부를 '상'으로 몰아 변별력 상실 → 오르막이 있을 때만 +1
- 핵심 근거가 없으면 '하' 대신 '보류'
- **LLM-as-a-judge 교차검증**(Claude·GPT 독립 채점): 엔진-judge 10/15·11/15, judge끼리 8/15 → [judge_comparison.md](archive/v1-rule-engine/judge_comparison.md)
- 한계: OSM이 관광지 경계를 못 찾아 300m 반경으로 측정, 작업이 4곳에서 중단

## 데이터 수집 (2026-11-02 저녁)

- Google 15곳 식별·주제(SerpApi 45회), Tripadvisor 13곳 × 150건(Apify 월 한도 소진), GPS 궤적(사용 가능 3곳), 공식 사실 15곳, 다낭 기후
- Google 리뷰 대량 수집 시도 실패: SerpApi 5건 한계(미해결 이슈), 비로그인 "제한된 보기", 자동화 브라우저 로그인 차단
- Reddit(Arctic Shift)은 표본 부족으로 근거 문장용만
- 출처별 법적 검토 → [design_b_serpapi.md §1-6](archive/v0-design/design_b_serpapi.md)

## 설계안 v0.1 → v0.2 → B (2026-11-02 오후)

- v0.1: 리뷰 기반 7개 차원 → "리뷰만 근거면 신뢰도가 낮다, 데이터를 실제로 구할 수 있나" 지적
- v0.2: 측정 데이터(고도·면적·기후·시설 수) → "체류 시간은 어림값, 고저차는 보여주기식, 식당 수로 휴식 판단은 붐비는 곳에서 틀림" 지적 → [design.md](archive/v0-design/design.md)
- B: SerpApi 리뷰 대량 수집 전제 → 시험 결과 5건 한계로 전제 붕괴 → [design_b_serpapi.md](archive/v0-design/design_b_serpapi.md)
- 데이터 출처 전면 조사 → [research/report_data_sources.md](research/report_data_sources.md)

## 1일차 기획 (2026-11-02)

- 멘토링 반영: 대상 50대 이상, 걸음 수 대신 관광지 난이도, 근거 DB + HITL → [../presentation/day1/pitch.md](../presentation/day1/pitch.md) · 최종 회의 [../meetings/2026-11-02_final_meeting.md](../meetings/2026-11-02_final_meeting.md)
