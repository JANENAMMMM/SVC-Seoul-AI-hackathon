# ScoringAI 워크플로우 그림 설명서

> 목적: ScoringAI 전체 흐름(수집 → DB 저장 → LLM 채점 → 검증 → 집계 → 활용)을 **그림 한 장**으로 그리기 위한 설명서. 그림을 그리는 사람(또는 Codex)은 이 문서만 보고 그릴 수 있어야 한다.
> 기준: v2.1, 2026-11-03. 수치는 Supabase 실제 행 수. 자세한 설명은 [README.md §3](README.md#3-구조).

---

## 0. 그림 요구사항

- **형식**: 가로 16:9 한 장. SVG(편집용)와 PNG(발표용, 1920×1080 이상) 둘 다. 파일 위치 `docs/scoring-ai/assets/workflow.svg`, `workflow.png`
- **흐름 방향**: 왼쪽에서 오른쪽. 6개 구역(레인)을 세로 띠로 나눔
  `① 데이터 수집` → `② 근거 DB` → `③ LLM judge` → `④ 검증` → `⑤ 집계·저장` → `⑥ 활용`
- **글자**: 한국어. 코드 이름(`scoring_evidence`, `list_evidence` 등)은 고정폭 글꼴로 그대로 표기
- **색 구분** (의미별로 일관되게)
  - 외부 데이터 출처: 회색
  - DB 테이블: 파란색 (원통 모양)
  - LLM(Claude): 보라색
  - 코드가 판정하는 단계(검증·집계): 초록색
  - 결과물·사용처: 주황색
  - 무효·검수 대기 경로: 빨간 점선
- **화살표 종류**
  - 실선: 데이터가 흐름
  - 점선 양방향: 도구 호출(질문 → 결과)
  - 빨간 점선: 실패·되돌림(재제출, 무효, 검수 대기)
- 모든 상자에 들어갈 문구는 아래 표의 "상자 문구"를 그대로 쓴다. 괄호 속 숫자는 행 수 또는 건수.

---

## 1. 구역 ① 데이터 수집 (회색, 왼쪽 끝)

외부 출처 6개를 세로로 쌓는다. 각 상자 → 구역 ②의 해당 테이블로 실선 화살표.

| 상자 이름 | 상자 문구 | 수집 방법 | 가는 곳 |
|---|---|---|---|
| S1 공식 사실 | 공식 사이트·안내문 웹 조사 / 계단 수·엘리베이터·케이블카·경로 길이·실내외·냉방 | 사람+AI 웹 조사, 출처 URL 기록 | `scoring_evidence` (`fact:` 86) |
| S2 GPS 궤적 | OpenStreetMap 공개 GPS 궤적 + Open-Meteo 고도 / 실제 걸은 거리·시간·오르막 | 관광지 구역으로 궤적 자르기 | `scoring_evidence` (`gps:` 36) |
| S3 지도 데이터 | OpenStreetMap Overpass / 300m 반경 보행로·계단·벤치·화장실 | 자동 질의 | `scoring_evidence` (`osm:` 35) |
| S4 Tripadvisor 리뷰 | Tripadvisor 리뷰 13곳 × 약 150건 (Apify) | 원문 저장 + 정규식으로 주제 언급 비율 계산 | 원문 → `scoring_reviews` (1,854) / 비율 → `scoring_evidence` (`rev:` 104) |
| S5 Google 지도 | Google 지도 장소 정보·리뷰 주제·리뷰 5건 (SerpApi) | 장소 식별 + 자동 추출 주제 | 장소 → `scoring_places` (15) / 주제 → `scoring_evidence` (`topic:` 250) / 리뷰 → `scoring_reviews` (140) |
| S6 기후 | Open-Meteo 과거 기상 / 다낭 월별 최고 체감온도 | 자동 | `scoring_evidence` (`climate:` 12) |

S1~S6 아래에 작은 상자 하나: **`load_evidence.py` — 수집 파일을 DB로 옮김 (같은 사실은 같은 ID)**. S1~S6의 화살표가 이 상자를 지나 구역 ②로 들어가도록 그려도 된다.

구역 하단 메모(작게): "Google 리뷰 대량 수집은 불가(장소당 5건 한계) · 리뷰 원문은 git에 올리지 않음"

---

## 2. 구역 ② 근거 DB — Supabase (파란색 원통 6개)

원통 6개를 위아래 두 묶음으로 나눈다.

**윗묶음 "채점 전에 채워지는 근거"**

| 원통 | 문구 | 안에 보여줄 예시 1줄 |
|---|---|---|
| D1 `scoring_places` | 관광지 15곳 / 이름·좌표·Google 정보 | `dad-02` 오행산 |
| D2 `scoring_evidence` | 근거 523건 / 차원·등급·값·단위·출처·**한계 메모** | `fact:dad-02:elevator` = 있음 (B) |
| D3 `scoring_reviews` | 리뷰 원문 1,994건 / 출처·언어·여행 유형·평점 | `rev:dad-02:<번호>` 리뷰 원문 한 건 (형식만 표시, 실제 문장 인용 X) |

D2 옆에 작은 범례: **근거 등급** A 측정 기후 · B 공식 사실·GPS(궤적 5개 이상) · C 지도 반경·리뷰 통계·GPS 표본 부족

**아랫묶음 "채점하면서 쌓이는 기록"**

| 원통 | 문구 |
|---|---|
| D4 `scoring_web_cache` | judge가 웹에서 찾아 인용한 페이지 103개 / URL·검색어·인용 문장 |
| D5 `scoring_judgments` | 채점 실행 원본 67회 / 출력·인용 통과 여부·토큰 |
| D6 `scoring_scores` | 최종 점수 17행(v2.1 15곳) / 차원 점수·종합·상태·조건 |

구역 위쪽 띠 문구: "모든 테이블은 `scoring_` 접두어 · 다른 팀 테이블 접근 안 함"

---

## 3. 구역 ③ LLM judge (보라색, 그림 중앙, 가장 크게)

큰 보라색 상자 **"Claude Sonnet judge (rubric v2.1)"** 안에 세로로 3단계.

1. **입력**: `place_id` 하나 + 규칙(차원 4개 정의, 차원별 앵커, 절차, "도구가 준 ID만 인용")
   - 작은 글씨: "근거는 프롬프트에 넣지 않고 도구로 직접 찾게 함"
2. **도구로 근거 찾기** (최대 12회) — 도구 아이콘 6개를 가로로
   | 도구 | 연결 (점선 양방향 화살표) |
   |---|---|
   | `get_place` | ↔ D1 |
   | `list_evidence` | ↔ D2 |
   | `search_reviews` | ↔ D3 |
   | `get_climate` | ↔ D2 (`climate:`) |
   | `web_search` | ↔ 구름 모양 "웹" (Anthropic 서버 검색, 최대 4회) |
   | `google_web_search` | ↔ 구름 모양 "웹" (SerpApi Google 결과) |
3. **`submit_scores`로 제출** — 제출 내용을 작은 카드로
   - 대표 관람 경로 (예: "오행산 투이선 — 엘리베이터 또는 계단, 동굴 2곳")
   - 차원 4개 × `typical` / `lower` / `upper` (1~10)
   - 조건: lower "엘리베이터 이용" [`fact:dad-02:elevator`] · upper "계단으로 정상" [`fact:dad-02:steps_count`]
   - 근거 ID 목록 · 근거로 쓴 수치 · 확신도(high/medium/low)

빨간 점선 되돌림 화살표(제출 → 제출): "형식 틀리면 1회 재제출 요청"

웹 구름 → D4 실선: "실제 검색 결과로 받은 URL 중 인용된 것만 저장"

---

## 4. 구역 ④ 검증 (초록색, `verify.py`)

judge 제출 카드 → 이 구역으로 실선. 체크리스트 상자 하나, 항목 4개에 체크 아이콘:

1. 점수 1~10 정수, `lower ≤ typical ≤ upper`
2. lower·upper가 typical과 다르면 조건이 있고, 조건마다 근거 ID
3. 인용 ID가 D2·D3·D4에 **실제로 있음** (URL은 `www.`·https 차이 무시) — D2·D3·D4에서 이 항목으로 가는 가는 점선("대조")
4. 인용 수치가 DB 원본 값과 5% 안에서 일치

출구 두 갈래:
- 초록 실선 "통과 → 이 차원 유효"
- 빨간 점선 "하나라도 어김 → 이 차원은 이번 실행 무효"

구역 아래 작은 숫자: "v2.1 실행 65회 중 56회 전 차원 통과"

---

## 5. 구역 ⑤ 집계·저장 (초록색)

상자 문구: **"같은 관광지를 3회 실행 → 유효한 실행만 차원별 중앙값"**

- 종합 점수 = climb×3 + walking×3 + heat×2 + crowd×1 의 가중평균 (코드 계산, LLM이 내지 않음)
- 등급 표시: 1~3 하 · 4~6 중 · 7~10 상
- 확신도: 3회 중 가장 낮은 값
- 분기:
  - 초록 "ok" → 공개 점수
  - 빨간 점선 "실행 간 차이 >2점 · 유효 실행 없음 · 무효 실행 있음 → `needs_review`(검수 대기)" → 사람 검수 아이콘(현재 껌탄 코코넛 마을, 참 조각 박물관)

저장 화살표:
- 실행마다 → D5 `scoring_judgments` + 파일 `judge/v2/<곳>_run<k>.json`
- 최종 → D6 `scoring_scores` + 파일 `scores_v2.json`

---

## 6. 구역 ⑥ 활용 (주황색, 오른쪽 끝)

위에서 아래로 실선 연결.

1. **`scores_v2.json`** → **관람 방식 카탈로그 `visit_modes_v2_1.json`**
   - 15곳 × 3방식: `standard` 일반 / `short` 이동 보조·짧은 관람 / `full` 전체 관람
   - 예: 오행산 short 5점 · standard 7점 · full 7점
2. **패키지 난이도** (`package_difficulty.py`)
   - 입력: 일정표(관광지·방식·일정표 출처·경로 메모)
   - 규칙: 하루 최고 점수 + 6점 이상 연속 방문마다 +1 (하루 최대 +2)
   - 예: 바나힐(6) → 오행산 전체(7) = 8점 / 오행산을 short로 바꾸면 6점
3. **API** (`api/scoring.py`) — 저장 파일만 읽음, DB·Claude 호출 없음
   - `GET /api/scoring/places` · `GET /places/{id}` · `POST /packages/evaluate`
4. 사용처 아이콘 3개: 동선 짜기 · 챗봇("왜 힘든지" 근거 설명) · 화면(점수·이유·출처 링크)

---

## 7. 그림 하단 띠 (얇게, 회색 글씨)

- **검증 계획(진행 전)**: 채점에 쓰지 않은 후기와 대조 · 사람 기준셋 ±1점 일치율
- **한계**: "50세 이상 보통 체력" 가정의 설계 점수, 실제 고객 체감 검증 전
- 범례: 색 6종 · 화살표 3종

---

## 8. 한눈에 보는 연결 목록 (그리기 점검용)

```
S1 공식사실 ─▶ load_evidence ─▶ D2 (fact 86)
S2 GPS     ─▶ load_evidence ─▶ D2 (gps 36)
S3 OSM     ─▶ load_evidence ─▶ D2 (osm 35)
S4 Tripadvisor ─▶ load_evidence ─▶ D3 (1,854) · D2 (rev 104)
S5 Google  ─▶ load_evidence ─▶ D1 (15) · D2 (topic 250) · D3 (140)
S6 기후    ─▶ load_evidence ─▶ D2 (climate 12)

judge ⇄ D1 (get_place) · D2 (list_evidence, get_climate) · D3 (search_reviews) · 웹 (web_search, google_web_search)
웹 ─▶ D4 (인용된 URL만)
judge submit_scores ─▶ 검증 ◀┄ D2·D3·D4 (ID·수치 대조)
검증 ─▶ 집계(3회 중앙값) ─▶ D5 (실행마다) · D6 + scores_v2.json (최종)
집계 ┄▶ needs_review ─▶ 사람 검수
scores_v2.json ─▶ visit_modes_v2_1.json ─▶ 패키지 난이도 · API ─▶ 동선 · 챗봇 · 화면
```

## 9. Codex에게 줄 지시문 (복사용)

```
docs/scoring-ai/workflow_diagram.md를 읽고, §0의 요구사항대로 그림 한 장을 만들어
docs/scoring-ai/assets/workflow.svg 와 workflow.png(1920x1080 이상)로 저장해.
상자 문구와 숫자는 문서 표를 그대로 쓰고 새로 지어내지 마.
§8 연결 목록의 화살표가 빠짐없이 있는지 마지막에 점검해.
글자가 겹치거나 잘리면 상자 크기를 키워. 한국어 글꼴은 Noto Sans KR 또는 Pretendard.
```
