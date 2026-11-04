# ScoringAI 변경 이력

> 최종 상태는 [README.md](README.md). 이 파일은 "무엇을 왜 바꿨는지"의 기록이다. 작업 중 상세 판단 로그는 [orchestration_log.md](archive/worklog/orchestration_log.md).

## v2.2 (2026-11-03) — 관광지별 사실은 웹 검색으로, 비용 약 70% 절감 · 92186b8

**왜**: ① 계단 수·엘리베이터 운행 같은 관광지별 사실은 공식 수치가 드물고(계단 수는 오행산 1곳, 블로그 추정) 시기마다 바뀐다. ② 15곳 채점에 약 $9는 운영 관점에서 낭비가 크다(실행 1회 입력 약 4.2만 토큰, 3회 고정 반복).

- **초기 조사 사실 숨김** (f9c62c7): `fact:` 86건을 judge 도구(`list_evidence`)와 인용 검증 대상에서 제외. DB 행은 남겨 되돌릴 수 있게 함. 프롬프트에 "관광지별 물리 사실은 DB에 없으니 웹 검색으로 확인·URL 인용" 명시. rubric `v2.1` → `v2.2`
- **프롬프트 캐싱**: `messages.create`에 top-level `cache_control` 추가. 도구 루프에서 매 턴 다시 보내던 도구 정의·시스템 프롬프트·이전 대화를 캐시에서 읽음. 사용량에 `cache_creation_input_tokens`·`cache_read_input_tokens` 기록
- **필요할 때만 반복** (`run_judge.enough`): 1회 실행이 전 차원 검증 통과 + 확신도 low가 아니면 종료, 2회가 모두 통과하고 차원별 차이 ≤1이면 종료, 아니면 최대 `--runs`(기본 3)까지. `--fixed`로 예전처럼 고정 반복 가능
- **강제 도구 호출 제거**: Sonnet 5.5는 `tool_choice` 강제(`type: tool`)를 400으로 거부 → 도구 한도 초과 시에도 `auto` + 제출 지시문으로 변경 (기존에는 한도 초과가 드물어 드러나지 않았음)
- **시험 결과 (오행산 1곳)**: 1회로 종료(검증 통과), 캐시 읽기 32,105 · 캐시 쓰기 14,271 · 일반 입력 10 토큰. 종합 7/5/8 상 (v2.1: 7/4/8). 관광지 1곳 비용 추정 약 $0.35 → 약 $0.07 (웹 검색 요금 별도)
- **15곳 v2.2 재채점 완료**: 실행 28회(1곳당 평균 1.9회; 1회 종료 8곳, 2회 1곳, 3회 6곳), 인용 검증 통과 22/28. 비용 **$2.36** (1곳당 $0.157, 실행당 $0.084) vs v2.1 $8.02 (1곳당 $0.535) → 약 70% 절감. 중단된 시도 포함 v2.2 누적 $5.52. 계산: `python -m src.scoring.cost_report` (Sonnet 5.5 단가, 웹 검색 $10/1,000회 포함, SerpApi 제외)
- **새 관광지 1곳 채점 비용**: 평균 $0.157(범위 $0.07~$0.30, 1회로 끝나면 중앙값 약 $0.11). 근거 수집(SerpApi 약 3회·Apify 약 150건)은 요금제 단위라 별도 → README §7-1
- **결과**: 등급 15곳 중 11곳 유지. 바뀐 곳: 오행산 상→중(7→6), 미케 해변 하→중(3→4), 아시아파크 하→중(3→4), 한시장 중→하(4→3). 검수 대기 7곳(호이안 구시가지·용다리·한시장·대성당·하이반·껌탄 + 참 박물관은 해소)
- **검수 대기 기준 완화** (`verify.aggregate`): 무효 실행이 있어도 남은 유효 실행이 2회 이상이고 서로 1점 이내로 일치하면 검수 대기로 보내지 않고 `notes`에만 기록. 유효 1회뿐이거나 2점 이상 벌어지면 기존대로 검수 대기. API 호출 없이 저장된 실행 기록으로 재집계(`run_judge --reaggregate`), 점수 변화 없음. 검수 대기 7곳 → **1곳(한시장: 유효 2회의 혼잡 점수가 2점 차이)**
- **무효 원인**: 7건 모두 인용 검증 실패. 6건은 웹 검색 결과에 없던 URL 인용(모델 기억 속 URL), 1건은 지어낸 ID(`get_place:dad-08:accessibility`). 검증 장치가 의도대로 걸러냄
- **집계 방식 변경** (`verify.aggregate`): 차원별 중앙값 → 중앙값에 가장 가까운 유효 실행 1개의 점수(medoid). 유효 2회의 중앙값이 어느 실행과도 일치하지 않아 출처 연결이 실패(아시아파크)했기 때문. v2.1 고정 3회에서도 무효 1회면 생길 수 있던 문제
- `run_judge`가 재채점 전에 해당 관광지의 이전 실행 파일을 지움(반복 횟수가 줄면 v2.1 기록이 섞이던 문제), 점수에 `name_ko` 추가
- 관람 방식 카탈로그 `data/scoring/visit_modes_v2_2.json` 생성, API 기본 경로 변경. 테스트 기대값 갱신(오행산 standard 7→6, 증거 ID는 `fact:` 대신 웹 URL, 검수 대기 예시 dad-09→dad-15)
- v2.2 재채점 중단 이력: 1차 전체 재채점(캐싱 전)은 5곳 진행 후 중단, 실행 기록 파일은 v2.1로 되돌림. DB `scoring_judgments`에는 중단 전 v2.2 실행 행이 남아 있음
- 시험 실행이 `scores_v2.json`·`dad-02_run1.json`을 덮어써 v2.1 카탈로그와 어긋남(테스트 2개 실패) → 파일은 v2.1로 되돌리고 시험 결과는 `data/scoring/archive/v2_2_trial/`과 DB에 보관. 15곳 재채점 후 한 번에 교체
- v2.1 결과 로컬 백업: `data/scoring/archive/v2_1/` (git 미포함, v2.1 파일은 git 이력에도 있음)
- 남은 일: 검수 대기 기준 재검토 (README·대본·그림 갱신은 아래 문서 항목에서 완료)

## 문서·그림 v2.2 갱신 (2026-11-04)

- README(§3 구조도·DB 행 수·집계 방식, §5 점수표, §7 테스트 수·재집계 명령, §8·§9·§10), `workflow_script.md`, `workflow_diagram.md`, 그림 생성 스크립트 2개의 숫자를 v2.2로 갱신하고 그림 3장을 다시 렌더링
- DB 행 수(2026-11-04): web_cache 242 · judgments 126 · scores 32. v2.2 최종 실행 28회 중 22회 통과, 웹 검색 17회, 검수 대기 1곳(한시장)
- v2.2 항목의 "실행 27회, 통과 20/27"을 실행 기록 파일·DB 대조 결과인 28회, 22/28로 정정(1곳당 $0.157은 그대로, 실행당 $0.084 = $2.36/28)

## 문서·그림 (2026-11-03) — aa51cc8 ~ 9764660

- README §3-1 DB 저장 내용(테이블 6개, 근거 접두어별 건수·등급·만드는 법·한계), §3-2 LLM이 근거를 읽고 검증받는 7단계 추가
- 근거 등급 정의 정정: v1 "A=GPS" → v2 "A=기후 측정, B=GPS(궤적 5개 이상)·초기 조사 사실, C=OSM 반경·리뷰 통계·GPS 표본 부족"
- 워크플로우 그림: 한 장짜리 전체 그림(`assets/workflow.png`)과 팀원 설명용 두 장(`workflow_1_evidence.png` 수집·정제·저장, `workflow_2_judging.png` 채점·검증) + 생성 스크립트(`gen_workflow.py`, `gen_workflow_full.py`)
- 그림·문서에서 "공식 사실" 출처 제거(사실 정보는 채점 때 웹 검색), 1장 그림을 출처 → 수집 → 정제 → 저장 표로 재구성
- `.gitignore`의 `*.png` 때문에 그림이 커밋에서 빠졌던 문제 → 그림 3장만 강제 추가
- 팀원 설명 대본 `workflow_script.md` (본문 약 4분 + 질의응답 부록 A~F)
- develop PR #14 생성, develop 병합 충돌(`api/main.py`·`pyproject.toml`·`uv.lock`) 해결 (e57ab9c)

## v2.1 후속 (2026-11-03, Codex) — 관람 방식·패키지·검증 도구 · 04eed98

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

- 근거 등급(v1 기준) A(GPS)·B(지도·공식)·C(리뷰), 차원 5개. ※ v2 DB에서는 A = 기후 측정, B = 공식 사실·GPS(궤적 5개 이상), C = OSM 반경·리뷰 통계·GPS 표본 부족으로 바뀜 → [README §3-1](README.md#3-1-db에-저장된-것-supabase-2026-11-03-기준-행-수), 규칙 판정 → [engine_spec.md](archive/v1-rule-engine/engine_spec.md)
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
