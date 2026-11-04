# 관광지 주변 식당 수집 (`src/restaurants`)

> 노희윤 · 2026-11-04

관광지 좌표를 넣으면, **관광지마다 추천 식당 5곳**과 각 식당의 **한국어 리뷰 원문**을 돌려줍니다.
**부모님 프로필은 받지 않습니다.** 해산물 기피·현지 음식 선호·한식 빈도 같은 프로필 반영은 모두 일정 엔진이 합니다(아래 "프로필은 어디서 반영하나").
기본은 규칙으로만 고르고 **아무것도 저장하지 않습니다.** 한식 여부는 선택적으로 Claude가 다시 판단할 수 있습니다(기본 꺼짐).

### 팀원이 꼭 지킬 것

1. **저장 규칙:** 일정 DB에는 식당의 **`place_id`만** 저장한다. 이름·평점·영업시간·리뷰 같은 식당 데이터는 저장하지 않고, 다시 보여줄 때 `fetch_place_for_display(place_id)`로 재조회한다.
2. **리뷰 규칙:** 리뷰는 **가공하지 않고 원문 그대로** 담는다 (키워드 태그·경고 같은 파생 정보를 만들지 않는다). 리뷰를 보여줄 때는 작성자를 함께 표시한다.

---

## 1. 흐름 (관광지 1곳)

```text
① 주변 식당 검색 (20곳) → ② 제외 → ③ 점수·상위 5곳 → ④ 리뷰 조회 → 결과 반환 (저장 X)
```

| 단계 | Google 호출 | 요금 등급 |
| --- | --- | --- |
| ① Nearby Search, 반경 1km, 최대 20곳 (카페·술집 제외) | 1회 | Enterprise |
| ③ 후보에 한식당이 없으면 한식당만 추가 검색 | 0~1회 | Enterprise |
| ④ 상위 5곳의 리뷰(최대 5개씩)·AI 리뷰 요약 | 최대 5회 | Enterprise + Atmosphere |

무료 사용량은 등급별 월 1,000회. 한 번 실행하는 동안 같은 식당 리뷰는 1번만 조회한다.

## 2. 고르는 로직

### ② 제외 (두 가지)

| 제외 조건 | 판단 방법 |
| --- | --- |
| 음식점이 아님 | 대표 타입이 `restaurant`, `*_restaurant`, `bistro`, `snack_bar`, `noodle_shop`, `food_court`, `steak_house`, `diner`가 아니면 제외. 검색은 "식당 타입이 포함된 곳"이라 대표 타입이 호텔·리조트·상점인 곳도 섞여 들어온다 (실측: `resort_hotel`, `hotel`, `grocery_store`) |
| 식사 시간에 문 닫는 날이 있음 | 요일마다 12:00 또는 18:30 중 하나라도 열어야 통과. 영업시간 정보가 없으면 제외하지 않고 `hours_unknown` 표시 |

프로필에 따라 달라지는 제외(해산물 전문점 등)는 여기서 하지 않는다. 같은 결과를 프로필이 다른 일정에 그대로 쓰도록 모두 남겨 두고, 일정 엔진이 거른다.

### ③ 점수

```text
기본 점수 = (리뷰 수 × 평점 + 50 × 기준 평점) / (리뷰 수 + 50)
            기준 평점 = 그 관광지 후보들의 평균 평점 (없으면 4.0)
```

리뷰가 적을수록 기준 평점 쪽으로 끌려가서, 리뷰 3개짜리 5.0점이 리뷰 2,000개짜리 4.6점보다 위로 가지 않는다.

점수는 평점과 리뷰 수만으로 계산한다. 현지 음식 선호 같은 프로필 보정은 넣지 않는다(엔진에서 더함).

**한식 포함** — 프로필과 상관없이 항상 적용한다.

1. 후보에 한식당(`is_korean_final`)이 없으면 한식당만 추가 검색(관광지당 1회).
2. 점수순 상위 5곳에 한식당이 없으면, 나머지 중 점수가 가장 높은 한식당을 **5위 자리와 교체**.

한식을 실제로 몇 끼 쓸지는 일정 엔진이 프로필(`korean_need`)로 정한다. 여기서는 엔진이 고를 수 있게 한식당을 데이터에 넣어 두기만 한다.

### 한식 판단: Claude (선택 기능, `src/restaurants/korean_check.py`)

Google 대표 타입은 한식 분류가 자주 틀린다 (베트남 닭밥집 "Cơm gà"가 `korean_restaurant`, 실제 한국식 치킨집이 일반 `restaurant`). 이름에 티가 안 나는 한식당도 있어서 규칙 대신 Claude가 판단한다.

| 항목 | 내용 |
| --- | --- |
| 켜는 법 | 원본 `collect(..., korean_judge=KoreanJudge())` — **기본 꺼짐** (요청마다 시간·비용이 들어서) |
| 대상 | ② 제외를 통과한 후보 전체. 관광지당 1회 묶음 호출, 같은 식당은 다시 묻지 않음(`place_id` 캐시) |
| 입력 | 식당 이름, Google 대표 타입(참고용, "틀릴 수 있음" 명시), 좌표, 관광지·도시 이름 |
| 판단 | 이름·위치로 판단, 모르는 곳만 웹 검색(호출당 최대 2회). 답은 `strict` 도구 호출로 `korean` / `not_korean` / `uncertain` + 한 줄 근거 |
| 한식 기준 | 한국 음식을 주로 파는 곳. 한식·한국식 BBQ·분식·치킨·한국식 중화요리(짜장·짬뽕)·매운 라면 포함. 한국인 운영이어도 메뉴가 주로 현지식이면 아님 |
| 반영 | **원본(`cuisine_tag`, `is_korean`)은 덮어쓰지 않고** `korean_check`(판단·근거·출처)를 옆에 붙인다. 최종 한식 여부는 `is_korean_final`: `korean`만 한식, `not_korean`·`uncertain`은 한식 아님. 한식 포함 규칙은 `is_korean_final` 기준 |
| 모델·비용 | Claude Haiku 5.5, effort low. 추정 비용이 예산(기본 $1)을 넘으면 `BudgetExceeded`를 낸다 |
| 필요한 키 | 루트 `.env`의 `ANTHROPIC_API_KEY` |

실측(다낭 13곳): Claude 호출 28회·웹 검색 14회, 추정 약 $0.19. "SC Restaurant & Bar"(Google은 한식)를 한식 아님으로, "Hawa's Food"(한국식 양념치킨)·"Mì Cay SEOUL"(한국식 매운 라면)을 한식으로 바로잡음.

### ④ 리뷰

- Google이 주는 리뷰(관련도순 최대 5개) 중 **원문이 한국어인 리뷰만** 골라 원문 그대로 담는다.
- AI 리뷰 요약(`reviewSummary`)은 리뷰가 아니라 Google이 만든 요약문 1개라서 있으면 그대로 담는다.
- 실측(다낭): `languageCode=ko` 요청 시 리뷰 70개 모두 한국어 원문, 요약은 14곳 모두 비어 있었다.
- **리뷰는 가공하지 않는다.** 키워드 태그를 세거나 "해산물 언급 2건" 같은 경고를 만들지 않고 원문 그대로 담는다. 리뷰 내용 판단은 LLM 단계에서 원문으로 한다.

### 프로필은 어디서 반영하나

이 모듈은 부모님 프로필을 받지 않는다. 데모 데이터와 원본 `collect()` 결과를 바꿔 끼워도 같은 방식으로 동작하고, 점수에 프로필 보정이 두 번 들어가는 일이 없다.

| 프로필 질문 | 반영하는 곳 | 방법 |
| --- | --- | --- |
| 1. 현지 음식 선호 `local_food` | 일정 엔진 (`meals.py`) | `is_local`인 식당에 점수 ±0.15 |
| 2. 한식 필요 `korean_need` | 일정 엔진 | 끼니마다 한식 슬롯을 정하고 `is_korean_final`로 고름 |
| 3. 피하는 식재료 `avoid_ingredients` | 일정 엔진 | 해산물은 `primary_type`으로 제외, 그 외 재료는 `ingredient_tags`가 채워지면 제외 |
| 4. 식사 장소 `venues` | 일정 엔진 | `venue_type`이 채워지면 거름 |

`venue_type`, `ingredient_tags`는 아직 이 모듈이 만들지 않는다(없으면 엔진이 거르지 않는다). 리뷰 문장을 읽어야 알 수 있는 판단은 LLM 단계에서 원문으로 한다.

## 3. 입력과 출력

**입력 ① 관광지** `[{ "id": "han-market", "name": "한 시장", "lat": 16.0684, "lng": 108.2241 }]`

**출력** — 관광지마다 식당 5곳과 제외된 식당·이유(`excluded`). 식당 1건의 필드는 아래 표와 같고, **덮어쓰는 필드는 없다** (다음 단계 LLM·화면이 어느 값을 믿을지 알 수 있게).

| 구분 | 필드 | 값의 출처 |
| --- | --- | --- |
| **유지** (Google 원본) | `place_id`, `name`, `lat`, `lng`, `primary_type`, `rating`, `rating_count`, `price_level`, `opening_text` | Google Places 응답 그대로 |
| **유지** (원본 타입으로 계산) | `cuisine_tag`, `is_korean`, `is_local` | Google `primary_type`을 우리 분류표로 바꾼 값. **Claude 판단으로 바뀌지 않는다** |
| **붙음** (우리가 계산) | `distance_m`(관광지 핀 기준 직선), `score`, `hours_unknown`, `pinned` | 우리 규칙 |
| **붙음** (한국어 리뷰) | `reviews.korean_reviews`(원문 그대로·작성자 포함), `reviews.summary`, `reviews.returned_count` | Google 리뷰, 가공 없음 |
| **붙음** (Claude, 켰을 때만) | `korean_check` = `{verdict, reason, checked_by}` | Claude 한식 판단. 안 켜면 `null` |
| **붙음** (최종 한식 여부) | `is_korean_final` | `korean_check`가 있으면 `verdict == "korean"`, 없으면 `is_korean`과 같음 |

**어느 값을 쓸지:** 원래 Google 분류가 궁금하면 `primary_type`·`cuisine_tag`·`is_korean`, **한식인지 최종으로 알려면 `is_korean_final`**, 근거는 `korean_check.reason`. `verdict`가 `uncertain`이면 한식 아님으로 처리됐다는 뜻이다 (`cuisine_tag`가 `korean`이어도 `is_korean_final`은 false일 수 있다).

## 4. 저장·리뷰 규칙

### 저장 규칙

| 데이터 | 저장 |
| --- | --- |
| `place_id` | ✅ 저장한다 |
| 위도·경도 | 저장하지 않는다 (필요하면 재조회) |
| 이름·평점·영업시간·리뷰 등 식당 데이터, 우리가 계산한 점수·분류·한식 판단 | ❌ 저장하지 않는다. 메모리에서만 쓴다 |

- 원본 `collect()`와 `scripts/collect_restaurants.py`는 결과를 돌려주기만 하고 파일·DB에 쓰지 않는다.
- 일정을 저장할 때는 식당마다 `place_id`만 넣고, 보여줄 때 `fetch_place_for_display(place_id)`로 다시 받는다.
- 실행 중 같은 식당의 리뷰는 한 번만 조회한다 (메모리 안에서만, 함수가 끝나면 사라진다).

### 리뷰 규칙

- Google이 주는 리뷰 중 **원문이 한국어인 리뷰만** 골라 **원문 그대로** 담는다. 요약·태그·경고 같은 파생 정보를 만들지 않는다.
- 리뷰를 화면에 보여줄 때는 **작성자를 항상 표시**한다 (`reviews.korean_reviews[].author`, `author_uri`).
- Google이 만든 AI 리뷰 요약(`reviewSummary`)이 있으면 그대로 담는다. 보여줄 때는 "리뷰 요약" 제목과 API가 준 `disclosureText`를 수정 없이 함께 표시하고, 우리 LLM이 만든 요약에는 `disclosureText`를 붙이지 않는다.

## 5. 미결정: 리뷰를 LLM(Claude)에 넣어 추천 사유 만들기

- 계획: 리뷰 원문(수정 없이) + 부모님 프로필을 Claude에 보내 추천 식당과 사유를 받는다. 저장은 안 한다.
- Claude 호출 코드는 그래프 통합 담당이 구현한다. 입력은 `CollectResult`(한국어 리뷰 원문)와 프로필 담당이 넘기는 프로필이다.

## 6. 한계

- [ ] **대표 타입 하나만 본다.** 대표 타입이 `restaurant`면 실제 베트남 식당이어도 `is_local`이 false이고, 이름에 "Seafood"가 있어도 해산물로 분류되지 않는다. 일정 엔진이 이 값을 그대로 쓰므로 현지 가점·해산물 제외도 같은 한계를 가진다.
- [ ] **원본은 Google 한식 분류를 그대로 쓴다.** Claude 판단을 켜면 `is_korean_final`로 바로잡히지만 기본은 꺼짐.
- [ ] **Claude 판단이 실행마다 흔들릴 수 있다.** `uncertain`은 웹 검색으로 한 번 더 확인하지만, 그래도 `uncertain`이면 한식 아님으로 처리된다
- [ ] **한식 포함에 최소 평점이 없다.** 실측에서 평점 3.3 한식당이 5위로 들어갔다.
- [ ] **같은 식당이 여러 관광지에 중복 추천된다.** 다낭 시내 4곳(용다리·한시장·대성당·참 박물관), 호이안 2곳이 서로 가까워 많이 겹친다.
- [ ] **외곽 관광지는 식당 품질이 낮다.** 영흥사·온천·미선은 리뷰 30개 미만 식당이 절반 이상.
- [ ] **해산물 외 재료·식사 장소 태그(`ingredient_tags`, `venue_type`)를 만들지 않는다.** 엔진은 태그가 있으면 쓰지만, 지금은 채우는 단계가 없다.
- [ ] **가정값:** 기준 리뷰 수 50, 식사 시각 12:00/18:30, 반경 1km, 카페·술집 제외 목록, 대표 타입 허용 목록. 근거 없이 정한 값이다.
- [ ] **리뷰는 식당당 최대 5개**라 대표성이 낮다.
- [ ] **Claude 비용은 추정치다.** 실제 금액은 Anthropic 콘솔 기준.

## 7. 실행

```bash
# 루트 .env 에 GOOGLE_API_KEY (Claude 한식 판단을 켜면 ANTHROPIC_API_KEY도)

# 원본: 결과는 화면에만 출력, 저장 없음
uv run python scripts/collect_restaurants.py \
  --attractions scripts/examples/attractions_danang.json \
  --city 다낭 --country VN --limit 1

uv run pytest tests/test_restaurant_cuisine.py tests/test_restaurant_pipeline.py tests/test_korean_check.py   # API 호출 없음
```

실행할 때마다 API를 다시 호출한다. 테스트는 관광지 1곳으로. 과금 방지는 Google Cloud 콘솔에서 Places API (New) 일일 할당량을 낮게 설정한다. Claude 판단은 `KoreanJudge(budget_usd=...)`로 상한을 둘 수 있다.

## 출처

- [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search) · [Place Details](https://developers.google.com/maps/documentation/places/web-service/place-details) · [Place types](https://developers.google.com/maps/documentation/places/web-service/place-types)
