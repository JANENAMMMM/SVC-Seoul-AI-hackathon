# ScoringAI v2 시범 실행 메모
> **참고: 이 문서는 v2.0 시험 실행(2곳×1회) 기록이다.** 최신은 v2.1(차원별 앵커, 15곳×3회) → `SUMMARY.md`, `judge_spec_v2.md`, `orchestration_log.md` 참조.


## 만든 것
- `src/scoring/db.py`: psycopg로 Supabase에 연결(`.env`의 `SUPABASE_DB_URL`). `scoring_*` 테이블 6개는 `CREATE TABLE IF NOT EXISTS`로만 만든다. 접두사가 다른 테이블은 코드에서 거부한다. DROP·TRUNCATE·ALTER는 쓰지 않았다. 실행 전 public 스키마에는 `hello_world_test` 하나만 있었고, 이 테이블은 건드리지 않았다.
- `src/scoring/load_evidence.py`: 수집 데이터를 고정 문자열 ID로 옮긴다. `fact:` `gps:` `osm:` `rev:` `topic:` `climate:` 형식이다. 근거마다 caveat를 붙였다.
  - GPS: 궤적 수 n, 5개 미만이면 "표본 부족"
  - OSM: "300m buffer, not site boundary"
  - 리뷰 regex 정밀도: 계단 약 90%, 대기 약 70%
  - 온천 'hot' 오탐
  - Tripadvisor regex 비율은 `rev:<site>:sig_<dim>`에 넣었다.
- `src/scoring/judge.py`: Messages API(`claude-sonnet-5-5`)로 도구 호출을 반복한다.
  - 클라이언트 도구: get_place, list_evidence, search_reviews(ILIKE), get_climate
  - 서버 웹 검색: `web_search_20250305`, 최대 4회
  - 최종 제출은 `submit_scores` 도구의 JSON 스키마로 받는다. 12회에 도달하면 이 도구를 강제로 호출한다.
  - 인용된 웹 URL은 `scoring_web_cache`(`web:<sha1[:10]>`)에 저장한다.
- `src/scoring/verify.py`: 다음을 검사하고 합산한다.
  - 인용 ID 실재 여부
  - 수치 대조(`numeric_claims`와 원본 값, 허용 오차 5%)
  - lower ≤ typical ≤ upper, 조건별 근거 ID 유무
  - 가중 종합(3/3/2/1, 반올림), 하/중/상 표시
  - 여러 실행의 중앙값. 폭이 2점을 넘거나 무효 차원이 있으면 `needs_review`
- `src/scoring/run_judge.py` CLI, `tests/test_scoring_v2.py`(합성 데이터 9개 테스트). `uv run pytest -q` 결과 18개 모두 통과.

## 테이블 건수
| 테이블 | 건수 |
|---|---|
| scoring_places | 15 |
| scoring_evidence | 523 (topic 250, rev 신호 104, fact 86, gps 36, osm 35, climate 12) |
| scoring_reviews | 1994 (Tripadvisor 13곳 원문 + Google 첫 페이지) |
| scoring_web_cache | 0 (웹 검색 미사용) |
| scoring_judgments | 2 |
| scoring_scores | 2 |

## 시범 결과 (`--runs 1`)
| 관광지 | climb | walking | heat | crowd | 종합 typical/lower/upper | 표시 | 도구 호출 | 토큰(입력/출력) |
|---|---|---|---|---|---|---|---|---|
| dad-02 오행산 | 8/5/9 | 7/5/8 | 7/4/9 | 5/4/7 | 7/5/8 | 상(lower 중) | 4 | 35,470/2,777 |
| dad-03 호이안 구시가지 | 1/1/2 | 5/3/7 | 7/4/9 | 6/4/8 | 4/3/6 | 중(lower 하) | 4 | 30,529/2,481 |

- 차원별 점수 표기는 typical/lower/upper 순서다.
- 인용 유효성: 두 곳 모두 4개 차원 전부 통과했다. 지어낸 ID는 없었고, `numeric_claims` 12건씩이 원본 값과 일치했다. status는 `ok`다.
- 비용: Sonnet 단가를 입력 $3, 출력 $15(100만 토큰당)로 가정하면 약 $0.28이다. 단가는 확인하지 않은 가정값이다.
- 조건 예시:
  - 오행산 climb lower: "엘리베이터 이용(편도 15,000 VND), 100~156계단 생략; 동굴·정상은 계단 필요"
  - 오행산 climb upper: "전체 관람 약 400계단"
  - 호이안 heat lower: "해진 뒤 저녁 또는 1월 방문"
- 출력 파일: `data/scoring/judge/v2/<site>_run1.json`, `data/scoring/scores_v2.json`

## 문제점
- 앵커와 어긋남: 오행산은 7(앵커 8), 호이안은 4(앵커 5)로 둘 다 앵커보다 1점 낮다. 앵커 관광지에 v2를 돌려 정렬하는 보정 단계가 필요하다. 앵커는 고정값으로 두거나 few-shot 예시로 주는 방안을 검토해야 한다.
- 웹 검색을 한 번도 쓰지 않아 웹 캐시와 인용 경로가 실제로 검증되지 않았다. 근거가 빈약한 관광지에서 따로 확인해야 한다.
- 실행을 1회만 해서 중앙값과 폭 검사(`needs_review`)는 아직 의미가 없다. 운영할 때는 `--runs 3`으로 돌려야 한다.
- crowd 차원은 근거가 2개뿐이고 regex 정밀도도 약 70%라 약하다.
- 수치 대조는 모델이 직접 적은 `numeric_claims`만 본다. rationale 본문에 쓴 수치는 검사하지 않는다.
