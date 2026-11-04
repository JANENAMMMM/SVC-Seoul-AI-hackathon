# HITL 피드백 루프 (해커톤 버전) — 사람이 고치고, AI가 근거로 다시 판단한다

> 2026-11-04 · 남재은 · 브랜치 `feat/scoring-hitl` · 그림: `python docs/scoring-ai/assets/gen_hitl.py`
> 상용화 고도화안(전체 버전)은 [hitl_roadmap.md](hitl_roadmap.md). 전체 구현은 `archive/scoring-hitl-full` 브랜치에 보관.

![HITL 피드백 루프](assets/hitl_loop.png)

## 원칙

- **개인 의견은 그 여행만 바꾸고, 관광지 점수는 MD 의견을 근거로 AI가 다시 채점한 뒤 승인해야 바뀐다.**
- LLM은 자연어를 구조로 바꾸고(Haiku), 근거를 보고 판정한다(Sonnet judge). 점수 합산과 일정 계산은 코드가 한다.
- 모든 조정은 **제안 → 승인**. 승인 전에는 일정도 점수도 바뀌지 않는다.

## 두 장면

| | 누가 | 흐름 | LLM |
|---|---|---|---|
| ① 점수 | 하나투어 MD | 의견 입력 → 조정안(장소·항목·주장) → [재채점] 의견을 `human:` 근거로 넣고 그 장소만 다시 채점(결과는 보관만) → 전후 점수·인용 근거 확인 → 승인 시 공개 점수 반영 | Haiku 1회 + Sonnet 1~3회 |
| ② 일정 | 자녀(부모님 의견 포함) | 자연어/버튼 → 수정 명령(기존 `feedback.py`) → 바뀐 일정 미리보기(기존 `refine`) → 자녀 승인 시 확정 | 자연어면 Haiku 1회, 버튼이면 0 |

일정 쪽 해석·재계산은 이지원·노희윤님의 `src/planner/feedback.py`·`edit.py`를 그대로 쓴다. 새로 더한 것은 "미리보기 → 승인" 단계와 기록이다.

## API (`api/hitl.py`)

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/hitl/itinerary/preview` | `{itinerary, commands?, feedback?, actor_role, actor_id}` → `{feedback_id, proposal}` (일정은 아직 안 바뀜) |
| POST | `/api/hitl/score/preview` | MD `{text, actor_id}` → 조정안·현재 점수 (점수는 아직 안 바뀜) |
| POST | `/api/hitl/score/{id}/rejudge` | 재채점 → 전후 점수, `human_cited`(의견 근거를 인용했는지) |
| POST | `/api/hitl/{id}/approve` | 일정: 확정 일정 반환 / 점수: 공개 점수·카탈로그 갱신 |
| POST | `/api/hitl/{id}/reject` | 거절(점수면 `human:` 근거 삭제) |
| GET | `/api/hitl/feedback?place_id=` | 조정 기록 |

- 프론트 연결(고객 화면 승인 버튼, MD 작업실 의견 입력)은 프론트 담당.
- 비용 보호: 해석은 사용자별 시간당 30회, 재채점은 하루 5회까지. 기존 `/api/planner/refine`의 자연어 해석은 서버 전체 시간당 60회. `HITL_MD_TOKEN`을 설정하면 MD 엔드포인트에 `X-MD-Token` 헤더가 필요하다.

## 저장

- `scoring_feedback`(마이그레이션 `supabase/migrations/20261104190000_scoring_hitl.sql`): 누가·무엇을·원문·해석 결과·상태(proposed → rejudged → applied/rejected)·전후 값·LLM 사용량
- 기존 `scoring_evidence`에 `human:<id>:<n>` 행만 추가(basis B, source `hanatour_md`). 테이블 구조 변경 없음
- 재채점 실행 기록은 `data/scoring/judge/hitl/<id>/`에 따로 두고, 승인 시 기존 기록은 `judge/v2/archive_hitl/<id>/`로 옮긴다(되돌리기 가능)
- 같은 마이그레이션의 `scoring_overrides`는 고도화안(임시 점수)용이다. 해커톤 버전에서는 쓰지 않는다(테이블은 비어 있음)

## 비용 (조정 1회당, 실측)

| 조정 | 호출 | 비용 |
|---|---|---|
| 일정 버튼 | 0 | $0 |
| 일정 자연어 / MD 의견 해석 | Haiku 1회 | 약 $0.0004~0.0006 (입력 약 2.3K · 출력 0.3~0.8K 토큰) |
| 점수 재채점(버튼 누를 때만) | Sonnet 1~3회 + 웹 검색 | 평균 $0.157, 범위 $0.07~0.30 (v2.2 15곳 실측) |

시연 규모(일정 조정 50회 + 재채점 5곳)는 약 $0.8.

## 발표 연결

- **AI 활용 구체성**: 의견을 구조로 바꾸고(Haiku), 사람 말을 그대로 믿지 않고 웹 근거로 교차 확인해 다시 채점(Sonnet + 인용 검증). `human_cited`로 AI가 의견을 근거로 썼는지 보여줄 수 있다.
- **실현가능성**: 일정 조정 1회 1원 미만, 재채점 1곳 약 200원. 기존 엔진·채점 파이프라인 재사용, 새 테이블 1개.
- 상용화 확장은 [hitl_roadmap.md](hitl_roadmap.md)의 "발표용 한 문장"을 쓴다.

## 확인한 것 / 하지 않은 것

- `uv run pytest` 217개 통과(HITL 6개: 해석 검증·strict 스키마·근거 행·호출 제한·일정 제안→승인)
- 실제 DB: 일정 제안→승인, MD 의견(실제 Haiku 1회)→조정안 기록·점수 불변→거절. 시험 행 삭제
- 재채점→승인: 저장된 오행산 실행 기록을 재생하는 가짜 judge로 게시·카탈로그 재생성까지 확인(전체 버전에서, 같은 코드). **실제 Sonnet 재채점은 아직 안 돌림**
