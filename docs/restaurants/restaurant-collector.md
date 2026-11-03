# 관광지 주변 식당 수집 (`src/restaurants`)

> 노희윤 · 2026-11-03 · 브랜치 `feat/restaurant-collector`
> 약관 해석은 원문을 읽은 팀 해석이며 법률 자문이 아닙니다.

관광지 좌표와 부모님 음식 취향(질문 4개)을 넣으면, **관광지마다 추천 식당 5곳**과 각 식당의 **한국어 리뷰 원문**을 돌려줍니다.
LLM 없이 규칙으로만 고르고, **아무것도 저장하지 않습니다.**

### 팀원이 꼭 지킬 것

1. 일정 DB에는 식당의 **`place_id`만** 저장한다. 다시 보여줄 때 `fetch_place_for_display(place_id)`로 재조회.
2. LangGraph **체크포인터를 DB로 바꾸면** state 안의 리뷰가 저장된다 → 리뷰를 state에 둔 채 DB 체크포인터 금지.
3. **LangSmith 트레이싱**은 노드 입출력을 서버에 기록한다 → 리뷰 다루는 노드는 트레이싱 끄기.
4. Places 데이터를 지도에 올릴 때는 **Google 지도만** (카카오맵·네이버 지도·OSM 불가).
5. 리뷰를 보여줄 때는 **작성자를 항상 표시**.

---

## 1. 흐름 (관광지 1곳)

```text
① 주변 식당 검색 (20곳) → ② 제외 → ③ 점수·상위 5곳 → ④ 리뷰 조회 → 결과 반환 (저장 X)
```

| 단계 | Google 호출 | 요금 등급 |
| --- | --- | --- |
| ① Nearby Search, 반경 1km, 최대 20곳 (카페·술집 제외) | 1회 | Enterprise |
| ③ 한식이 필요한데 한식당이 없으면 한식당만 추가 검색 | 0~1회 | Enterprise |
| ④ 상위 5곳의 리뷰(최대 5개씩)·AI 리뷰 요약 | 최대 5회 | Enterprise + Atmosphere |

무료 사용량은 등급별 월 1,000회. 한 번 실행하는 동안 같은 식당 리뷰는 1번만 조회한다.

## 2. 고르는 로직

### ② 제외 (두 가지만)

| 제외 조건 | 판단 방법 |
| --- | --- |
| 식사 시간에 문 닫는 날이 있음 | 요일마다 12:00 또는 18:30 중 하나라도 열어야 통과. 영업시간 정보가 없으면 제외하지 않고 `hours_unknown` 표시 |
| 해산물을 피하는데 해산물 전문점 | 대표 타입이 `seafood_restaurant`, `oyster_bar_restaurant`, `sushi_restaurant`, `fish_and_chips_restaurant` |

**해산물만 제외하는 이유:** 식재료 중 Google 장소 타입으로 확인되는 건 해산물뿐이다. 돼지고기·유제품·견과류는 해당 타입이 없고, 추정해서 빼면(예: 유제품 → 피자집) 괜찮은 식당까지 빠진다.

### ③ 점수

```text
기본 점수 = (리뷰 수 × 평점 + 50 × 기준 평점) / (리뷰 수 + 50)
            기준 평점 = 그 관광지 후보들의 평균 평점 (없으면 4.0)
```

리뷰가 적을수록 기준 평점 쪽으로 끌려가서, 리뷰 3개짜리 5.0점이 리뷰 2,000개짜리 4.6점보다 위로 가지 않는다.

**현지 음식 보정 (질문 1)** — 대표 타입이 여행지 국가의 현지 음식점일 때만 더한다 (예: 베트남 `vietnamese_restaurant`).

| 답 | 보정 |
| --- | --- |
| 익숙한 음식 위주 | −0.15 |
| 골고루 / 잘 모르겠어요 | 0 |
| 새로운 현지 음식 적극적으로 | +0.15 |

**한식 포함 (질문 2)** — "하루 한 끼 이상" 또는 "2~3일에 한 번"일 때만:

1. 후보에 한식당(`korean_restaurant`, `korean_barbecue_restaurant`)이 없으면 한식당만 추가 검색.
2. 점수순 상위 5곳에 한식당이 없으면, 나머지 중 점수가 가장 높은 한식당을 **5위 자리와 교체**.

"가끔 / 없어도 됨 / 잘 모르겠어요"는 강제하지 않는다 (점수로 들어오면 나옴).

### ④ 리뷰

- Google이 주는 리뷰(관련도순 최대 5개) 중 **원문이 한국어인 리뷰만** 골라 원문 그대로 담는다.
- AI 리뷰 요약(`reviewSummary`)은 리뷰가 아니라 Google이 만든 요약문 1개라서 있으면 그대로 담는다.
- 실측(다낭): `languageCode=ko` 요청 시 리뷰 70개 모두 한국어 원문, 요약은 14곳 모두 비어 있었다.
- **리뷰는 가공하지 않는다.** 키워드 태그를 세거나 "해산물 언급 2건" 같은 경고를 만들지 않는다. 리뷰로 새 콘텐츠를 만드는 건 Google 약관 3.2.3(c)(콘텐츠 생성 금지)에 걸릴 수 있어서, 리뷰 내용 판단은 LLM 단계에서 원문으로 한다.

### 부모님 음식 취향: 여기서 쓰는 것 vs LLM에 넘기는 것

| 질문 | 여기서 (규칙) | LLM에 넘김 (리뷰 원문과 함께) |
| --- | --- | --- |
| 1. 현지 음식 선호 `local_food` | ✅ 현지 음식점 점수 ±0.15 | ✅ 리뷰에서 맛·향이 강한지 판단 |
| 2. 한식 필요 `korean_need` | ✅ 한식당 추가 검색·상위 5곳에 1곳 포함 | - |
| 3. 피하는 식재료 `avoid_ingredients`, `avoid_other` | ✅ **해산물만**: 해산물 전문점 제외 | ✅ **전부** (해산물·돼지고기·유제품·견과류·기타): 리뷰에서 해당 재료 언급 판단 |
| 4. 식사 장소 `venues` | - | ✅ 리뷰에서 노점·길거리 분위기 판단 |

여기서는 Google 장소 타입과 평점처럼 **구조화된 값으로 확실히 판단되는 것만** 쓰고, 리뷰 문장을 읽어야 알 수 있는 건 전부 LLM에 넘긴다. 결과(`CollectResult.preference`)에 취향 전체가 그대로 담겨 다음 노드로 넘어간다.

## 3. 입력과 출력

**입력 ① 관광지** `[{ "id": "han-market", "name": "한 시장", "lat": 16.0684, "lng": 108.2241 }]`

**입력 ② 음식 취향** (프로필 담당이 넘겨줄 값)

| 질문 | 필드 | 값 |
| --- | --- | --- |
| 1. 현지 음식을 얼마나 즐기시나요? | `local_food` | `familiar` · `mixed` · `adventurous` · `unknown` |
| 2. 한식이 얼마나 필요한가요? | `korean_need` | `daily` · `every_2_3_days` · `occasional` · `none` · `unknown` |
| 3. 피하시는 식재료 (복수) | `avoid_ingredients` / `avoid_other` | `seafood` · `pork` · `dairy` · `nuts` / 직접 입력 단어 |
| 4. 식사 장소 (복수) | `venues` | `restaurant` · `street_food` · `unknown` |

어떤 값을 여기서 쓰고 어떤 값을 LLM에 넘기는지는 2장 표 참고.

**출력** — 관광지마다 식당 5곳: `place_id`, 이름, 좌표, 대표 타입, 한식/현지 여부, 평점, 리뷰 수, 가격대, 영업시간, 거리, 점수, 한국어 리뷰(작성자·링크 포함), 리뷰 요약. 제외된 식당과 이유도 함께.

## 4. 저장 규칙 (Google 약관) ⚠️

| 데이터 | 저장 |
| --- | --- |
| `place_id` | ✅ 무기한 (서비스별 약관 3조) |
| 위도·경도 | ⚠️ 30일까지 (14.3) |
| 이름·평점·영업시간·리뷰 등 나머지, 우리가 계산한 점수 | ❌ (서비스 약관 3.2.3) |

> **3.2.3(a) No Scraping.** Customer will not export, extract, or otherwise scrape Google Maps Content for use outside the Services. For example, … (iii) copy and save business names, addresses, or user reviews …
>
> **3.2.3(b) No Caching.** Customer will not cache Google Maps Content except as expressly permitted under the Maps Service Specific Terms.
>
> **3.2.3(c) No Creating Content From Google Maps Content.** Customer will not create content based on Google Maps Content. … (vii) use Google Maps Content to improve machine learning and artificial intelligence models …
>
> **14.2** Customer must not use Google Maps Content from the Places API in conjunction with a non-Google map.

**의도치 않게 저장되는 곳:** 일정 DB, DB 체크포인터, LangSmith 트레이싱, 로그·디버그 파일, 프론트 localStorage.

**화면 표시:** 리뷰는 작성자 표시 필수. AI 리뷰 요약을 보여줄 땐 "리뷰 요약" 제목 + API의 `disclosureText`(수정 금지) + 신고·리뷰 보기 링크. 이 규칙은 Google이 만든 요약용이라 우리 LLM 결과에 `disclosureText`를 붙이면 안 된다.

## 5. 왜 Google 리뷰인가

| 출처 | 결정 | 근거 |
| --- | --- | --- |
| 네이버 블로그 | ❌ | 검색 API 약관 2.3 "데이터를 AI에 입력하거나 … 활용하는 행위" 금지, 가공·저장 금지. 블로그 robots.txt가 AI·RAG 목적 봇 접근 금지 |
| 티스토리 (카카오 검색) | ❌ | 카카오 답변: "검색 데이터를 외부 LLM API로 전송하여 활용하는 것은 제한" |
| Google 리뷰 | ✅ | 공식 API, 크롤링 불필요, 한국어 원문 리뷰가 실제로 나옴 |

## 6. 미결정: 리뷰를 LLM(Claude)에 넣어 추천 사유 만들기

- 계획: 리뷰 원문(수정 없이) + 부모님 취향을 Claude에 보내 추천 식당과 사유를 받는다. 저장은 안 한다.
- 약관상 걸리는 점: 저장을 안 해도 3.2.3(a) 서비스 밖으로 꺼내기, (c) 콘텐츠 생성에 해당할 수 있다. LLM 생성을 명시적으로 허용하는 건 **Maps Experience agent tools**(서비스별 약관 10장, MCP)를 쓸 때뿐이다.
- 진행: Google Maps Platform 지원팀에 문의 중. 답이 오기 전 데모 방침은 팀이 결정.

## 7. 한계

- [ ] **대표 타입 하나만 본다.** 대표 타입이 `restaurant`면 실제 베트남 식당이어도 현지 보정이 안 되고, 이름에 "Seafood"가 있어도 해산물 제외가 안 된다. 호텔·카페도 섞일 수 있다.
- [ ] **한식 포함에 최소 평점이 없다.** 실측에서 평점 3.3 한식당이 5위로 들어갔다.
- [ ] **"2~3일에 한 번" = "하루 한 끼"로 처리된다.** 관광지마다 판단해서 관광지 3곳이면 한식당 3곳. 일정(날짜) 단계에서 나눠야 한다.
- [ ] **같은 식당이 여러 관광지에 중복 추천될 수 있다.**
- [ ] **해산물 외 재료·식사 장소는 규칙 단계에서 반영되지 않는다.** LLM 단계(6장)가 정해져야 반영된다.
- [ ] **가정값:** 보정 ±0.15, 기준 리뷰 수 50, 식사 시각 12:00/18:30, 반경 1km, 카페·술집 제외 목록. 근거 없이 정한 값이다.
- [ ] **리뷰는 식당당 최대 5개**라 대표성이 낮다.

## 8. 실행

```bash
# 루트 .env 에 GOOGLE_API_KEY
uv run python scripts/collect_restaurants.py \
  --attractions scripts/examples/attractions_danang.json \
  --prefs scripts/examples/food_prefs_example.json \
  --city 다낭 --country VN --limit 1
uv run pytest tests/test_restaurant_cuisine.py tests/test_restaurant_pipeline.py   # API 호출 없음
```

결과는 화면에만 출력되고 실행할 때마다 다시 호출한다. 테스트는 관광지 1곳으로. 과금 방지는 Google Cloud 콘솔에서 Places API (New) 일일 할당량을 낮게 설정.

## 출처

- [Google Maps Platform Terms of Service](https://cloud.google.com/maps-platform/terms) · [Service Specific Terms](https://cloud.google.com/maps-platform/terms/maps-service-terms) · [Places API 정책](https://developers.google.com/maps/documentation/places/web-service/policies?hl=ko) · [Maps Experience agent tools](https://developers.google.com/maps/ai/grounding-lite)
- [Nearby Search](https://developers.google.com/maps/documentation/places/web-service/nearby-search) · [Place types](https://developers.google.com/maps/documentation/places/web-service/place-types)
- [NAVER API 이용약관](https://developers.naver.com/products/intro/terms/terms.md) · [blog.naver.com/robots.txt](https://blog.naver.com/robots.txt) · [카카오 데브톡 답변](https://devtalk.kakao.com/t/api-llm/151458)
