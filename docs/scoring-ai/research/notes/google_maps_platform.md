# Google Maps Platform: 관광지 체력 부담 추정용 공식 데이터 (2026-11 기준)

## Q1. Places API (New) 필드, SKU tier, 리뷰 5개 제한, AI 요약 제공 지역

### Takeaway
체력 부담에 쓸 만한 필드는 대부분 비싼 **Enterprise + Atmosphere** tier에 있다(`reviews`, `reviewSummary`, `generativeSummary`, `editorialSummary`, `goodForChildren`, `parkingOptions`, `restroom`). 리뷰는 장소당 **최대 5개**이고 relevance 순이다. AI 요약 두 가지는 **베트남/동남아에서 제공되지 않는다**(공식 지원 목록에 없음).

### Cited Findings
- SKU tier(Place Details 기준. Text/Nearby Search도 대체로 같음):
  - Essentials: `types`, `location`, `formattedAddress`, `addressDescriptor`, `viewport` 등
  - Pro: `accessibilityOptions`, `displayName`, `primaryType`, `businessStatus`, `entrances`, `navigationPoints`, `subDestinations`, `containingPlaces`, `googleMapsUri`, `timeZone`
  - Enterprise: `rating`, `userRatingCount`, `regularOpeningHours`, `currentOpeningHours`, `priceLevel`, `priceRange`, `websiteUri`, `transitStation`
  - Enterprise + Atmosphere: `reviews`, `reviewSummary`, `generativeSummary`, `editorialSummary`, `neighborhoodSummary`, `goodForChildren`, `goodForGroups`, `parkingOptions`, `restroom`, `allowsDogs`, `routingSummaries`, `paymentOptions` 등 — [Place Data Fields](https://developers.google.com/maps/documentation/places/web-service/data-fields)
  - 참고: `photos`는 Place Details에서는 IDs Only, Text Search에서는 Pro — 같은 출처
- `accessibilityOptions` 하위 필드(모두 boolean): `wheelchairAccessibleParking`, `wheelchairAccessibleEntrance`, `wheelchairAccessibleRestroom`, `wheelchairAccessibleSeating` — [Place resource reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places)
- `reviews[]`는 장소당 최대 5개이고 "sorted by relevance"다. 리뷰에는 `visitDate`(방문 연·월로 잘라서 제공)가 있다 — [Place resource reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places)
- 리뷰 표시 정책에 "default order is relevance"라는 문구가 있고, 정렬·필터 방식을 사용자에게 고지해야 한다 — [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies)
- `generativeSummary`(AI place summary, 약 100자)는 Culture, Entertainment and Recreation 등의 type에만 있고, **영어로 India와 United States에서만** 제공된다. "Summarized with Gemini" 문구와 `overviewFlagContentUri`를 표시해야 한다 — [Place summaries](https://developers.google.com/maps/documentation/places/web-service/place-summaries)
- `reviewSummary`(AI review summary)의 제공 범위는 영어(미국, 영국, 인도, 일본, 중남미 다수), 일본어(일본), 포르투갈어(브라질), 스페인어(중남미·미국)다. **베트남과 동남아 국가는 목록에 없다.** `reviewSummary.reviewsUri` 링크와 `disclosureText`("Summarized with Gemini")를 표시해야 한다 — [Review summaries](https://developers.google.com/maps/documentation/places/web-service/review-summaries)

### Inferences
- 다낭 관광지에서 실제로 쓸 수 있는 신호는 리뷰 5개 본문, `rating`/`userRatingCount`, `accessibilityOptions`, `regularOpeningHours`, `editorialSummary`(있을 때만), `parkingOptions`, `restroom`, `subDestinations`/`entrances` 정도다. 예를 들어 Marble Mountains처럼 큰 장소는 하위 장소와 입구 수로 규모를 가늠할 수 있다.
- 리뷰 5개만으로는 계단이나 경사 언급이 표본 편향을 피하기 어렵다. 보조 신호로만 쓰는 것이 맞다.

### Gaps
- reviews 정렬 옵션: reference에서 `reviewsSort` 같은 요청 파라미터를 찾지 못했다(페이지 마지막 약 1.7k자는 읽지 못함). 레거시 Place Details에는 `reviews_sort=newest|most_relevant`가 있었던 것으로 기억하지만 이번에 확인하지 못했다.
- 각 SKU의 1,000건당 가격과 무료 한도는 pricing 페이지를 열어보지 못했다.

## Q2. 리뷰를 5개보다 많이 받는 합법적 방법, Places Aggregate, Places Insights

### Takeaway
공식 API로 남의 장소 리뷰 전체를 가져오는 방법은 확인되지 않았다. Places Aggregate API는 장소 개수와 place ID 목록만 돌려준다. Places Insights(BigQuery)는 집계 통계용이고 리뷰 본문은 없는 것으로 보인다.

### Cited Findings
- Places Aggregate API는 지정 영역(원, 지역, 폴리곤) 안에서 type, 운영 상태, price level, rating으로 필터링한 장소를 다룬다. 반환값은 `INSIGHT_COUNT`(개수)와 `INSIGHT_PLACES`(place ID 목록, 개수가 100 이하일 때만)다. 세부 정보는 Place Details로 따로 조회해야 한다 — [Places Aggregate overview](https://developers.google.com/maps/documentation/places-insights/overview)
- Places Insights는 BigQuery 기반 집계 제품이다. place types, ratings, store hours, wheelchair accessibility, brands 같은 속성을 다룬다. "Get Started"와 "Contact sales" 경로가 있고, 개요 페이지에는 국가 커버리지(베트남 포함 여부)와 집계 임계값이 나와 있지 않다 — [Places Insights](https://developers.google.com/maps/documentation/placesinsights)

### Inferences
- 관광지 10~20곳을 개별로 평가하는 데는 Aggregate나 Insights가 거의 쓸모없다. Aggregate는 "주변 화장실·카페 밀도" 같은 보조 지표 정도로만 쓸 수 있다.

### Gaps
- Business Profile API가 소유자나 관리자만 리뷰에 접근할 수 있다는 점은 이번에 1차 문서로 확인하지 못했다. 일반적으로 알려진 사실은 그 API의 `accounts.locations.reviews`가 자기 소유 위치에만 동작한다는 것이다. 다만 미검증이므로 https://developers.google.com/my-business 에서 확인해야 한다.
- Places Insights의 지역 커버리지와 스키마 필드 목록은 미확인이다(schema reference 페이지를 확인해야 함).

## Q3. Popular times / 체류 시간("people typically spend X here")

### Takeaway
공식 Places API 필드 카탈로그에 popular times, live busyness, typical visit duration은 **없다**. 이 데이터를 얻으려면 스크래핑(ToS 위반)이나 서드파티(BestTime 등)를 써야 한다.

### Cited Findings
- Place resource와 data fields 목록에 해당 필드가 없다. 가장 가까운 필드는 `Review.visitDate`와 opening hours다 — [Place resource reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [Place Data Fields](https://developers.google.com/maps/documentation/places/web-service/data-fields)
- (2차 출처, 벤더) Popular Times는 Maps/Search UI에만 나오고 API 필드가 아니라고 한다 — [BestTime blog](https://blog.besttime.app/popular-times-api-alternative-for-developers/), [apiserpent](https://apiserpent.com/blog/google-maps-popular-times-api-data). 스크래퍼 상품도 있다: [Apify](https://apify.com/crawlerbros/google-maps-popular-times). 이는 공식 경로가 아니다.

### Gaps
- Google이 "API로 제공하지 않는다"고 명시한 1차 문서는 찾지 못했다. 부재를 확인한 근거는 필드 목록뿐이다.

## Q4. Routes, Elevation, Street View, 3D Tiles, Gemini Grounding with Google Maps

### Takeaway
Elevation API는 경로를 따라 고도를 샘플링할 수 있어(최대 512좌표) **계단과 언덕의 고도차 정량화에 가장 유용**하다. Gemini Maps grounding은 답변 텍스트와 출처(이름, URL)만 돌려주고 영어 전용이다.

### Cited Findings
- Elevation API는 해발 고도를 미터 단위로 돌려준다. 경로 샘플링에서는 최대 512좌표를 넣을 수 있고, 결과마다 `resolution`(m)이 붙는다. 직접 데이터가 없는 지점은 주변 4개 지점 값으로 보간한다 — [Elevation overview](https://developers.google.com/maps/documentation/elevation/overview)
- Gemini API의 Grounding with Google Maps:
  - 응답 출처 annotation에는 source URL과 name만 있다. 리뷰, 사진, 영업시간은 모델이 내부에서만 쓴다.
  - 가격: Gemini 3 이상은 월 5,000건 무료 후 1,000 검색쿼리당 $14다. 2.5 이하는 grounded prompt 1,000건당 $25다.
  - 지원 모델: 2.5 계열과 3.x 계열.
  - 프롬프트와 응답은 영어만 지원한다.
  - 출처는 내용 바로 뒤에 표시해야 하고 "Google Maps" 표기를 그대로 써야 한다.
  - 출처: [Gemini Maps grounding](https://ai.google.dev/gemini-api/docs/maps-grounding)
- **불일치 주의:** 이전 버전 문서에서는 `placeId`, `reviewSnippets`, `googleMapsWidgetContextToken`을 반환한다고 기억한다. 그러나 이번에 가져온 요약에서는 확인되지 않았다. 원문을 다시 확인해야 한다(같은 URL).

### Inferences
- 다낭 해발 관측 지점을 연결한 path(입구에서 정상·주요 지점까지)로 Elevation을 조회하면 누적 상승고를 계산할 수 있다. 이것이 Google 공식 데이터 중 가장 객관적인 체력 지표다. 단, 계단은 해상도 한계 때문에 과소평가될 수 있다.

### Gaps
- Routes API의 WALK 모드 거리·시간, 경로 고도 미지원 여부, Street View Static, Photorealistic 3D Tiles, Maps Grounding Lite/MCP는 이번 세션의 도구 예산 안에서 1차 문서를 확인하지 못했다. 후속 확인 대상: https://developers.google.com/maps/documentation/routes , https://developers.google.com/maps/documentation/streetview , https://developers.google.com/maps/documentation/tile/3d-tiles
- Elevation 가격과 캐싱 정책은 overview 페이지에 나와 있지 않다.

## Q5. ToS: 캐싱, 저장, 파생 점수, 표시와 attribution

### Takeaway
**place ID는 무기한 저장할 수 있다.** lat/lng는 최대 30일 연속 캐시한 뒤 삭제해야 한다. 그 외 Places content(리뷰 원문 포함)는 일반 ToS의 캐싱·파생 금지 조항을 따르므로 DB에 장기 저장하면 안 된다. 따라서 **"place_id + 우리 팀이 산출한 점수"만 저장하고 원문은 필요할 때 다시 조회하는** 설계가 안전하다.

### Cited Findings
- "You can therefore store place ID values indefinitely." 즉 place ID는 캐싱 제한에서 면제된다 — [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies)
- "Customer can temporarily cache latitude (lat) and longitude (lng) values from the Places API for up to 30 consecutive calendar days, after which Customer must delete..." 이 문구는 2020년판과 2024년판 Service Specific Terms에서 동일하다 — [Service Terms 2024-04-22](https://cloud.google.com/maps-platform/terms/maps-service-terms/index-20240422), [2020-06-14](https://cloud.google.com/maps-platform/terms/maps-service-terms/index-20200614)
- 2023년판에서는 Directions, Geocoding, Roads 등의 lat/lng에도 같은 30일 규정이 있다 — [Service Terms 2023-08-28](https://cloud.google.com/maps-platform/terms/maps-service-terms/index-20230828)
- 표시 의무:
  - Google Maps 로고(높이 16–19dp)나 "Google Maps" 텍스트(Roboto, `translate="no"`, 현지화 금지)를 표시한다.
  - Places content를 다른 콘텐츠와 시각적으로 구분한다.
  - 리뷰에는 작성자 avatar(최소)·이름·프로필 링크를 붙이고, `googleMapsUri`로 원문에 접근할 수 있게 한다.
  - 리뷰 정렬 방식을 고지한다.
  - 출처: [Places API policies](https://developers.google.com/maps/documentation/places/web-service/policies)
- AI 요약을 표시할 때는 "Summarized with Gemini" 문구를 넣어야 한다 — [Place summaries](https://developers.google.com/maps/documentation/places/web-service/place-summaries), [Review summaries](https://developers.google.com/maps/documentation/places/web-service/review-summaries)

### Inferences
- 리뷰 텍스트를 LLM으로 분석해 만든 "체력 점수"는 Google Maps Content에서 파생된 콘텐츠로 해석될 위험이 있다. 일반 ToS 3.2.3의 파생물 생성 금지 조항과 충돌할 수 있다. 점수에 Elevation, 현장 조사, 공공데이터 같은 비Google 근거를 섞으면 리스크가 줄어든다. 이 부분은 법률 판단이 아니라 추론이다.

### Gaps
- 현행(2026) Service Specific Terms와 일반 ToS 3.2.3 원문은 페이지가 잘려서 직접 인용하지 못했다. 위 내용은 과거 버전 아카이브에 근거한다. 확인할 곳: https://cloud.google.com/maps-platform/terms , https://cloud.google.com/maps-platform/terms/maps-service-terms
- 파생 점수 저장이 명시적으로 허용되는지 금지되는지에 대한 Google 1차 문구는 찾지 못했다.
