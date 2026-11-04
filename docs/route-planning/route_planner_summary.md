# 일정 엔진 핵심 요약

브랜치 `feat/route-planner` · 자세한 설명은 [route_planner.md](route_planner.md)

## 한 줄 요약

부모님 프로필 + 고른 관광지 + 일수를 넣으면 **날짜별 일정표**(관광지·식사·이동·휴식)가 나오고,
**정해진 수정 명령 9개**로만 다시 짠다. LLM은 일정을 직접 쓰지 않는다.

## 되는 것 / 아직 안 되는 것

| 되는 것 | 아직 안 되는 것 |
|---|---|
| 일정 생성·수정 API 2개 | **자연어 피드백 → 명령 변환(LLM)** ← 이어서 할 부분 |
| 도보·택시 이동, 연속 보행 한도, 휴식 | 실제 길찾기(이동은 직선거리 추정) |
| 점심·저녁 식당 선택, 한식 빈도, 식당 고정·교체 | 식당 태그(`venue_type` 등) 실데이터 반영 확인 |
| 영업시간·휴무 반영, 난이도 상한(재은님 모듈) | 직접 입력한 기피 재료(`avoid_other`) 반영 |
| 테스트 153개 통과 | `set_food_pref`, `avoid_ingredient`, `suggest_alternatives` 명령 |

## API

| 엔드포인트 | 용도 |
|---|---|
| `POST /api/planner/plan` | 일정 생성 (`travelers`, `place_ids`, `days`, `start_date`) |
| `POST /api/planner/refine` | 명령으로 일정 수정 (`itinerary`, `commands`) |

서버는 저장하지 않는다. 수정할 때는 **이전 응답 전체(`state` 포함)를 그대로 다시 보낸다.**

## LLM이 연결할 지점

자연어 피드백을 아래 명령 목록으로 바꿔 `/refine`의 `commands`에 넣으면 된다.

| `op` | 필드 | 동작 |
|---|---|---|
| `lighten_day` | `day` | 그날 관광지를 줄인 코스(`short`)로 |
| `add_place` | `place_id`, `day?` | 관광지 추가 |
| `remove_place` | `place_id` | 관광지 제거 |
| `move_place` | `place_id`, `day` | 다른 날로 이동 |
| `set_mode` | `place_id`, `mode` | 관람 방식 변경 |
| `more_korean_meals` | - | 한식 빈도 한 단계 상향 |
| `set_pace` | `pace` | 느리게 / 보통 / 빠르게 |
| `swap_restaurant` | `day`, `meal` | 그 끼니 식당 교체 |
| `adjust_walk_limit` | `direction` | 연속 보행 한도 한 단계 조정 |

- 명령이 하나라도 잘못되면 **일정은 그대로**이고 `clarification`에 되묻는 문장이 온다. 화면에 그대로 보여주면 된다.
- `change_summary`는 무엇이 바뀌었는지 요약이다. 일정 검토 코멘트(`review_comment`)는 비어 있어서 LLM이 채울 수 있다.
- 명령 없이 자연어(`feedback`)만 보내면 "LLM 변환 미연결" 안내(`NO_LLM_MESSAGE`)가 온다.

## 식당 JSON이 지켜야 할 것

| 필드 | 용도 |
|---|---|
| `place_id`, `name`, `lat`, `lng`, `primary_type` | 기본 정보 |
| `rating`, `rating_count`, `score`, `opening_text` | 품질·영업시간 필터 |
| `is_korean_final` (없으면 `is_korean`) | 한식 슬롯 |
| `is_local`, `pinned` | 현지 취향 가점, 관광지 내 고정 식당(바나힐 뷔페) |
| `venue_type` | `restaurant` / `street_food` / `unknown` — 프로필 `venues`로 거름 |
| `ingredient_tags` | `pork/seafood/dairy/nuts` 중 확인된 것, **없으면 `[]`** — 피하는 재료와 겹치면 제외 |
| `tag_confidence`, `tag_evidence` | 거르는 데는 안 쓰고 사용자 설명용으로 전달 |

태그 필드가 없는 파일도 그대로 동작하고, 이때는 일정의 `assumptions`에 안내가 붙는다.
파일 경로는 `data/restaurants/restaurants_danang.json` 또는 환경변수 `RESTAURANTS_JSON`.

## 실행·테스트

```bash
uv run uvicorn api.main:app --reload
uv run --python 3.11 pytest -q      # Python 3.10.0에서는 pytest가 내부 오류로 죽어서 3.11 필요
```

## 알아둘 한계

- 이동시간은 **직선거리 × 도로 보정 ÷ 35km/h** 추정이다. 실제 길찾기가 아니다.
- 체류시간(60/120/240분)과 보행 한도 등 `config.json` 값 상당수는 **가정값**이다.
- 방식(`short`)을 바꿔도 체류시간은 그대로이고 걷는 시간·난이도만 달라진다.
- 시내에서 먼 관광지(45분 이상) 날은 저녁이 항상 들어가지만, 일찍 끝나면 저녁까지 빈 시간이 길다.
- 먼 권역에서 일찍 끝나는 날은 외진 곳(예: 미선)에서 저녁을 먹는다.
