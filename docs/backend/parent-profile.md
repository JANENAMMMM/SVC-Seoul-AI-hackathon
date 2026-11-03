# 부모님 프로필 API

부모님의 체력·식성 설문 응답을 받아 보행속도를 계산해 정규화된 프로필을 돌려준다.
저장은 하지 않는다 (요청마다 계산해서 바로 응답).

## 엔드포인트

```
POST /api/profile
```

```bash
curl -X POST localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"age": 67, "gender": "female"}'
```

응답 예시:

```json
{
  "age": 67,
  "gender": "female",
  "walking_speed": { "age_band": "65~69세", "base_speed_mps": 1.0525 },
  "walking_duration": null,
  "local_food": "unknown",
  "korean_need": "unknown",
  "avoid_ingredients": [],
  "avoid_other": [],
  "venues": ["unknown"]
}
```

## 필드

| 필드 | 타입 | "잘 모르겠어요" 처리 |
|---|---|---|
| `age` | `int` | - |
| `gender` | `"female" \| "male"` | - |
| `walking_speed` | `{age_band, base_speed_mps}` | 계산값. **50세 미만이면 `null`** |
| `walking_duration` | `under_15min \| 15_30min \| 30_60min \| 1_2hour \| over_2hour \| null` | `null` |
| `local_food` | `familiar \| mixed \| adventurous \| unknown` | `"unknown"` |
| `korean_need` | `daily \| every_2_3_days \| occasional \| none \| unknown` | `"unknown"` |
| `avoid_ingredients` | `list[seafood \| pork \| dairy \| nuts]` | `[]` (없음/모름 구분 안 함) |
| `avoid_other` | `list[str]` ("기타" 직접 입력 단어) | `[]` |
| `venues` | `list[restaurant \| street_food \| unknown]` | `["unknown"]` |

`local_food`/`korean_need`/`avoid_ingredients`/`avoid_other`/`venues`는 `feat/restaurant-collector`
브랜치의 `FoodPreference`(`src/restaurants/preferences.py`)와 이름·타입·기본값이 동일하다 —
그 모듈을 소비하는 쪽에서 이 응답을 그대로 넣을 수 있다.

## 범위 밖

- DB 저장 없음 (추후 공용 trip 스키마에 붙일 예정)
- 보행속도로 일정 밀도·동선을 정하는 로직 없음 (`m/s` 값만 제공)
- 생활형 질문(계단, 연속보행 등) 기반 보행속도 보정 없음
  (끼워 넣을 자리는 `src/profile/schema.py`의 `WalkingSpeed` 주석 참고)

## 코드 위치

`src/profile/` (schema, walking_speed, service) · `api/routes/profile.py` · `tests/test_profile.py`
