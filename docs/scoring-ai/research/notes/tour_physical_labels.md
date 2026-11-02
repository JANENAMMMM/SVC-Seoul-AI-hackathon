# 투어 마켓플레이스·운영사의 구조화된 체력 난이도 라벨 (50+ 여행자, 다낭)

## Viator Partner API v2의 `additionalInfo` 체력/접근성 enum, 접근 등급, 데이터 사용

### Takeaway
확인됨. Viator Partner API v2의 `AdditionalInfo.type`에는 `PHYSICAL_EASY` / `PHYSICAL_MEDIUM` / `PHYSICAL_HARD`와 휠체어·유모차 접근성, 건강 제한 enum이 있습니다. 이 데이터가 담긴 `/products/{product-code}`는 Basic-access Affiliate 등급에서도 호출할 수 있습니다. 대량 수집용 엔드포인트(`/products/modified-since`, `/products/bulk`)는 Full-access 이상에서만 열립니다.

### Cited Findings
- `AdditionalInfo` 스키마의 설명은 "An additional information fact to communicate to travelers regarding this product"이고 `type`만 필수입니다. 문서에 나열된 `type` 값은 "one of (but not limited to)"로 표기되며 다음과 같습니다. `OTHER`, `WHEELCHAIR_ACCESSIBLE`, `NOT_WHEELCHAIR_ACCESSIBLE`, `STROLLER_ACCESSIBLE`, `PETS_WELCOME`, `PUBLIC_TRANSPORTATION_NEARBY`, `INFANTS_MUST_SIT_ON_LAPS`, `INFANT_SEATS_AVAILABLE`, `TRANSPORTATION_WHEELCHAIR_ACCESSIBLE`, `SURFACES_WHEELCHAIR_ACCESSIBLE`, `NO_BACK_PROBLEMS`, `NO_PREGNANT`, `NO_HEART_PROBLEMS`, `HEALTH_OTHER`, `PHYSICAL_EASY`, `PHYSICAL_MEDIUM`, `PHYSICAL_HARD` — [Viator Partner API technical docs (OpenAPI 렌더링 HTML, curl로 받아 직접 확인)](https://docs.viator.com/partner-api/technical/)
- 각 항목에는 `description`(사용자에게 보여 줄 자연어 문장)이 함께 오며, `Accept-Language`에 따라 번역됩니다. — [같은 문서](https://docs.viator.com/partner-api/technical/)
- 스펙의 응답 예시에서 확인한 description 문구: `PHYSICAL_EASY` → "Suitable for all physical fitness levels". 문서 안에는 "Not recommended for travelers with poor cardiovascular health"(`NO_HEART_PROBLEMS`에 대응하는 것으로 추정), "Not recommended for travelers with spinal injuries"(`NO_BACK_PROBLEMS`에 대응하는 것으로 추정)도 있습니다. — [같은 문서](https://docs.viator.com/partner-api/technical/)
- 2024년 10월 changelog: "Removed COVID-19 safety attributes from AdditionalInfo schema". — [Viator Partner API docs](https://docs.viator.com/partner-api/technical/)
- 접근 등급: Basic-access Affiliate는 "a limited subset of the non-transactional endpoints"만, Full-access Affiliate는 모든 non-transactional 엔드포인트를 쓸 수 있습니다. 엔드포인트별 표에서 Basic-access는 `/products/{product-code}` ✅, `/products/search` ✅, `/search/freetext` ✅, `/attractions/search` ✅, `/attractions/{attraction-id}` ✅, `/destinations` ✅이고, `/products/modified-since` ❌, `/products/bulk` ❌, `/reviews/product` ❌입니다. — [같은 문서](https://docs.viator.com/partner-api/technical/); [Golden Path – Basic Access](https://partnerresources.viator.com/travel-commerce/affiliate/basic-access/golden-path/?source=specs)
- 문서에는 상품 데이터를 "ingested and managed on your local system"하거나 실시간으로 호출할 수 있다고 적혀 있습니다(1회 초기 수집 후 delta update). — [같은 문서](https://docs.viator.com/partner-api/technical/)

### Inferences
- `PHYSICAL_*` 3단계는 공급사가 상품(투어) 단위로 입력하는 값입니다. 관광지 자체의 라벨이 아니므로, 관광지 체력 부담의 약한 참고 라벨(weak label)로만 쓸 수 있습니다. 같은 Ba Na Hills라도 투어마다 값이 다를 수 있습니다.
- 3단계뿐이라 해상도가 낮습니다. 대신 `NO_HEART_PROBLEMS`, `NO_BACK_PROBLEMS`, `WHEELCHAIR_ACCESSIBLE` 등과 묶으면 50+ 여행자용 보조 특징으로 쓸 수 있습니다.
- Basic-access로도 상품 검색과 상세 조회가 되므로, 다낭 destination의 상품을 검색해 상세를 하나씩 조회하는 방식으로 표본을 모을 수 있어 보입니다. 다만 rate limit과 약관을 확인해야 합니다.

### Gaps
- `PHYSICAL_MEDIUM` / `PHYSICAL_HARD`의 표준 description 문구는 스펙 예시에서 찾지 못했습니다. 요청서에 적힌 "Travelers should have a moderate physical fitness level"은 미검증입니다. 공급사 입력 화면의 정의도 확인하지 못했습니다.
- "Most travelers can participate"는 Viator 스펙에서 찾지 못했습니다. 아래 리셀러 페이지에서만 보이며, 이 문구는 `additionalInfo`가 아니라 별도 필드에서 오는 것으로 추정되지만 미검증입니다.
- 데이터 저장·2차 활용(ML 라벨로 쓰는 것) 관련 약관 원문은 확인하지 못했습니다. 파트너 계약서나 Terms를 별도로 봐야 합니다.

## Da Nang 상품 페이지 스팟체크

### Takeaway
부분 확인입니다. Ba Na Hills 투어 리셀러 페이지에서 Viator식 문구("Most travelers can participate", "Not recommended for travelers with spinal injuries")는 보였습니다. 하지만 Viator·Tripadvisor 원 페이지는 403으로 막혀 직접 확인하지 못했습니다.

### Cited Findings
- Pelago의 Ba Na Hills 상품 페이지에 "Most travelers can participate", 심장 질환자 비권장, 휠체어·유모차 불가 정보가 있습니다. — [Pelago](https://www.pelago.com/en-SG/activity/pc522yb0a-explore-ba-na-hills-from-danang-da-nang/) (검색 스니펫 기준)
- Magpie의 Ba Na Hills Premier Tour에 같은 문구와 임신부 비권장이 있습니다. — [Magpie](https://magpie.travel/things-to-do/ba-na-hills-premier-tour/71ff7cee-611c-4465-91e2-0e1af3eae147) (스니펫)
- Lokalee 페이지 제목이 "Not recommended for travelers with spinal injuries"입니다. — [Lokalee](https://www.lokalee.app/en/tours/exploring-ba-na-hills-full-day-tour)
- Tripadvisor "Discover Bana Hills Tour" 페이지는 존재하지만 fetch 결과가 403이었습니다. — [Tripadvisor](https://www.tripadvisor.com.au/AttractionProductReview-g298085-d18956642-Discover_Bana_Hills_Tour-Da_Nang.html)

### Inferences
- 문구가 Viator 스펙과 같으므로 Viator 데이터를 받아 쓰는 리셀러일 가능성이 높습니다(추정).

### Gaps
- Marble Mountains, Hoi An old town, My Son은 확인하지 못했습니다. Viator 페이지에 `PHYSICAL_*` 라벨이 실제로 붙어 있는지도 미확인입니다. API 키로 직접 조회하거나 브라우저로 확인해야 합니다.

## GetYourGuide / Klook / KKday

### Takeaway
GetYourGuide, Klook, KKday 모두에서 구조화된 체력 필드를 확인하지 못했습니다.

### Cited Findings
- GetYourGuide Partner API 스펙은 GitHub에 공개되어 있습니다. 검색으로 확인한 개요에는 접근성·체력 필드가 보이지 않았습니다. — [getyourguide/partner-api-spec](https://github.com/getyourguide/partner-api-spec)
- 참고로 Google Things to do feed spec에는 `wheelchair-accessible` 카테고리 라벨이 있습니다. — [Google feed spec](https://developers.google.cn/travel/things-to-do/reference/feed-spec/product-category)

### Gaps
- GYG 스펙 본문(YAML)에서 필드를 grep하지 못했습니다. 다음 단계로 확인이 필요합니다. Klook과 KKday는 조사하지 못했습니다(공개 API 문서 없음, 미검증).

## 투어 운영사의 체력 등급 정의

### Takeaway
Intrepid의 1~5 정의는 원문으로 확인했습니다. G Adventures는 원문을 찾지 못했고, Exodus는 Easy~Tough 척도라는 개요만 확인했습니다.

### Cited Findings
- Intrepid 원문
  - 1/5: "these trips are a relaxing break. You don't have to worry about doing anything physically demanding unless you want to."
  - 2/5: "Some easy physical activities included in your trip. No physical preparation is required to make the most of the journey."
  - 3/5: "This trip will raise your heart rate. Moderate physical activities are included and a good level of fitness is required."
  - 4/5: "Be prepared for some serious physical activity... most activities will be challenging."
  - 5/5: "Our highest physical rating... plenty of challenges and some extreme conditions... seriously fit."
  - 출처: [Intrepid Physical ratings](https://www.intrepidtravel.com/us/about/physical-rating)
- Intrepid는 등급이 완전한 분석이 아니므로 일정을 함께 읽으라고 안내하고, 짐 운반과 대중교통 이용도 고려하라고 합니다. — [Intrepid BE](https://www.intrepidtravel.com/be/about/physical-rating) (검색 요약 기준)
- Exodus는 모든 여행에 Activity Level(Easy~Tough)을 붙입니다. 정의는 여행 유형별(Walking/Hiking & Trekking, Cycling, Culture/Wildlife/Polar/Multi-Activity & Family, Winter)로 다릅니다. — [Exodus Activity Levels](https://www.exodus.co.uk/activity-levels)
- Odysseys Unlimited는 1~5 척도이며, 최저 등급은 하루 1~2마일 보행입니다. — [Odysseys Unlimited](https://www.odysseys-unlimited.com/physical-activity-levels-on-tour/) (스니펫)

### Inferences
- 이 등급들은 다일 투어 단위 라벨입니다. 단일 관광지 라벨로 쓰려면 기준을 다시 매핑해야 합니다. 정량 기준(보행 거리 등)이 있는 Odysseys 방식이 50+ 대상 루브릭 설계에 더 쓸모 있어 보입니다.

### Gaps
- G Adventures의 1~5 정의 원문은 찾지 못했습니다(미검증). Exodus 등급별 세부 정의도 하위 페이지를 열지 못해 확인하지 못했습니다.
