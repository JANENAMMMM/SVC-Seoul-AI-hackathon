# 공개 방문 후기와 ScoringAI v2.1 대조 — 2026-11-03

## 판정 범위

관광지 15곳의 v2.1 `typical` 점수와 공개 검색으로 확인한 **방문자 후기의 부담 요인**을 대조했다. 후기는 계단·보행·더위·혼잡이 실제 관람 방식에 따라 나타나는지 확인하는 데 사용했다. 검색 결과는 관련성·노출 순서에 따라 선택되므로 무작위 표본이 아니다. 원래 모델이 Tripadvisor 후기 일부를 이미 근거로 사용했으므로 이 대조는 **독립적인 정확도 검증이 아니며 일치율로 표시하지 않는다**. 후기의 별점은 난이도 점수로 바꾸지 않았다. 링크 안의 플랫폼 소개문·AI 요약은 판정 근거에서 제외하고, 개인 방문 후기만 사용했다.

| 관광지 (typical) | 후기에서 확인한 부담 요인 | 대조 | 근거 |
|---|---|---|---|
| 바나힐 (6) | 넓은 부지의 긴 보행, 골든브릿지 인파. 산정 기온은 시내보다 시원하다는 후기도 있음 | 방향 일치. 더위는 장소·계절 세분 필요 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d2255351-Reviews-or10-Ba_Na_Hills_SunWorld-Da_Nang.html) |
| 오행산 (7) | 엘리베이터를 타도 동굴의 미끄럽고 고르지 않은 계단이 남음. 고령자에게 불편하다는 후기 | 강한 일치. 노면·낙상 위험은 4차원 밖 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d454980-Reviews-or10-The_Marble_Mountains-Da_Nang.html) |
| 호이안 구시가지 (4) | 평지 보행은 쉽지만 오래 걸으며 저녁에는 인파, 낮에는 더위 | 조건부 일치. 시간대에 따라 혼잡과 더위가 반대 방향 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298082-d4507121-Reviews-Hoi_An_Ancient_Town-Hoi_An_Quang_Nam_Province.html) |
| 영흥사 (4) | 상단 도착 후 짧은 관람도 가능하나 실외 더위와 투어 단체 혼잡을 겪은 후기 | 대체로 일치. 하차 위치 확인 필요 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d5531576-Reviews-Lady_Buddha-Da_Nang.html) |
| 미케 해변 (3) | 평탄한 산책과 쉼 가능. 모래가 뜨겁고 긴 모래 보행은 별도 부담 | 짧은 관람에는 일치 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d7687457-Reviews-My_Khe_Beach-Da_Nang.html) |
| 용다리 (2) | 쇼 때 20~30분 전부터 인파 속 입석 대기, 종료 뒤 차량 호출을 위해 추가 보행 | **쇼 관람 일정에는 낮게 보일 수 있음**. 비쇼 관람과 분리 필요 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d6612108-Reviews-Dragon_Bridge-Da_Nang.html) |
| 한시장 (4) | 좁은 통로, 더운 실내, 낮 시간 혼잡 | 일치. 실내라고 더위가 낮지는 않음 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d5599000-Reviews-Han_Market-Da_Nang.html) |
| 다낭 대성당 (2) | 외관 사진 위주면 짧지만 내부 출입은 제한될 수 있음 | 외관 관람에는 일치. `full` 방식의 실현성 확인 필요 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d12273530-Reviews-Da_Nang_Catheral-Da_Nang.html) |
| 참 조각 박물관 (2, needs_review) | 여러 최근 후기에서 냉방 부재와 답답한 실내 더위를 언급 | **더위 typical 2점 재검토 우선** | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d454979-Reviews-Da_Nang_Museum_of_Cham_Sculpture-Da_Nang.html) |
| 아시아파크 (3) | 검색된 후기에서 한산했다는 사례가 있으나 시기·구역별 차이를 판단할 표본 부족 | 판정 보류 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298085-d8291301-Reviews-Asia_Park-Da_Nang.html) |
| 누이탄타이 온천 (5) | 찾은 방문 후기만으로 셔틀 사용 여부와 전 구역 도보 부담을 분리하기 어려움 | 판정 보류 | [방문 후기 목록](https://www.tripadvisor.com/Attraction_Review-g298085-d13384709-Reviews-Hot_spring_Park-Da_Nang.html) |
| 미선 유적지 (5) | 전동차 이후 도보가 필요하고, 야외 더위·단체 도착 뒤 혼잡 언급 | 일치. 전동차가 보행을 없애지는 않음 | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g16806420-d317894-Reviews-My_Son_Sanctuary-Duy_Phu_Duy_Xuyen_District_Quang_Nam_Province.html) |
| 하이반 고개 (3) | 검색된 투어 후기는 짧은 차량 정차를 설명하지만 관문 계단·관람 시간의 부담을 분리하지 못함 | 판정 보류 | [방문 후기](https://www.tripadvisor.com/AttractionProductReview-g293926-d25177053-Hue_to_Hoi_An_Jeep_Tour_via_Hai_Van_Pass-Hue_Thua_Thien_Hue_Province.html) |
| 호이안 야시장 (3) | 혼잡과 오래 걷기를 언급하며 이동이 불편하면 피하라는 후기 | **일반적인 야시장 일정에는 낮게 보일 수 있음** | [방문 후기](https://www.tripadvisor.com/Attraction_Review-g298082-d8091207-Reviews-Hoi_An_Night_Market-Hoi_An_Quang_Nam_Province.html) |
| 껌탄 코코넛 마을 (3, needs_review) | 찾은 방문 후기에서 더위 언급은 있으나 승하선·균형 부담을 점수와 대조할 표본 부족 | 판정 보류. 승하선 별도 확인 필요 | [방문 후기](https://www.tripadvisor.com/AttractionProductReview-g298082-d27942146-Experience_Basket_Boat_Ride_in_Water_Coconut_Forest-Hoi_An_Quang_Nam_Province.html) |

## 판단과 다음 검증

이 검색은 **설계의 방향을 점검하는 반례 탐색**으로 유용했다. 오행산·바나힐·미선의 이동 방식별 차이는 후기가 뒷받침한다. 참 조각 박물관의 더위, 용다리 쇼와 호이안 야시장의 혼잡·체류 부담은 우선 재검토할 지점이다. 검색 결과의 부족은 부담이 없다는 뜻이 아니다.

더 강한 검증은 관광지별로 **현재 채점에 쓰지 않은 후기**를 날짜·언어·관람 방식 기준으로 일정 수 미리 뽑고, AI 점수를 가린 평가자가 네 차원의 부담을 독립 코딩하는 것이다. 기존 Tripadvisor 원문과 중복되지 않는지 후기 ID·작성일로 확인한다. 50세 이상 고객에 대한 타당성은 별도로 가이드·상품기획자 평가와 실제 일정표의 관람 방식·체류 시간·차량 하차 위치를 대조해야 한다. 이후 장소별·차원별 일치/불일치 및 ±1점 이내 비율을 계산한다.

## Google 검색·Google Maps 공개 화면 추가 확인

Google 검색으로 공개 Google Maps 장소 페이지에 색인된 후기를 확인했다. 이것은 Google Places API 호출이나 전체 Google 리뷰 수집이 아니다.

| 장소 | Google Maps 공개 화면에서 확인한 내용 | 기존 판정에 미치는 영향 |
|---|---|---|
| [오행산](https://www.google.com/maps/search/Visit%2BMarble%2BMountains%2C%2BDa%2BNang%2B%26%2BHoi%2BAn%2C%2BVietnam) | 공개 후기에서 엘리베이터 하차 후 동굴 사원까지도 짧은 오르막이 남는다고 설명. Google의 후기 주제에는 steep/slippery stairs가 표시됨 | `short`가 무계단이 아니라는 판단을 재확인. 단, 주제 언급 수는 이미 원 채점의 보조 근거여서 독립 검증에 쓰지 않음 |
| [용다리](https://www.google.com/maps/search/Explore%2BDragon%2BBridge%2C%2BDa%2BNang%2C%2BVietnam) | 공개 후기와 주제에서 주말 쇼·인파가 확인됨 | 쇼 관람 방식과 일반 관람 방식을 분리할 이유를 보강. 주제 언급 수는 독립 검증 수치로 사용하지 않음 |

다른 13곳은 이번 Google 검색에서 동일 관광지의 **직접 후기 본문**을 안정적으로 확인하지 못했거나, 호텔·투어 상품 등 다른 개체가 섞여 결과를 제외했다. 특히 이름이 비슷한 장소의 후기를 대신 인용하지 않았다.

## 실제 서비스의 도구 호출 경로

현재 `judge.py`는 Anthropic의 `web_search` 서버 도구와 **SerpApi 기반 `google_web_search` 사용자 정의 도구**를 등록한다. 후자는 `SERPAPI_KEY`로 Google 웹 검색의 organic result(제목·URL·요약)를 반환한다. 기존 데이터 수집 때 사용한 키를 재사용하지만 **Google 공식 API는 아니다**. Google Maps의 장소별 직접 후기를 정식으로 가져오려면 Places API (New)의 Place Details에서 `reviews`를 요청하는 별도 도구가 필요하다. Google 공식 문서상 한 요청에 반환되는 후기는 **최대 5건**이며, `reviews` 필드는 Place Details Enterprise + Atmosphere 과금 계층이다. 검색 결과 페이지를 읽는 것과 50세 이상 체감 검증용 대량 후기 표본을 얻는 것은 다른 요구다.

기존 키로 `Da Nang Museum of Cham Sculpture no air conditioning review`를 **실제 1회 검색해 organic result 3건을 수신**했다. 이는 검색 도구의 연결 확인이며 Claude가 이 도구를 호출해 재채점하는 실행은 하지 않았다. 검색 결과는 제목·URL·짧은 요약이므로, 점수의 핵심 근거로 채택할 때는 반환된 원문 페이지를 별도로 확인해야 한다.

추가 구현 시 `get_google_place_reviews(place_id)` 도구가 기존 `google_place_id`를 받아 Place Details를 호출하고, 반환된 리뷰의 ID·날짜·언어·원문·Google Maps 링크를 출처로 보존하도록 한다. API 키는 서버 환경 변수에만 둔다. 5건 제한 때문에 이 도구는 **최신 사례 확인용**으로 쓰고, 정량 검증은 별도의 미사용 후기 표본과 사람 평가로 한다. Google의 공식 **Gemini Grounding with Google Search**도 현재 이용 가능한 도구 호출 경로다. 다만 Gemini API 키와 별도 모델 호출이 필요하다. Google 웹 검색 결과를 JSON으로 반환하는 기존 Custom Search JSON API는 공식 문서상 **신규 고객에게 닫혔고 2027-01-01 종료 예정**이므로 새 연동의 기본안으로 잡지 않는다.

문서: [SerpApi Google Search API](https://serpapi.com/search-api), [Gemini Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search), [Places API Place Details](https://developers.google.com/maps/documentation/places/web-service/place-details), [Places API 리뷰 제한](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [Custom Search JSON API 상태](https://developers.google.com/custom-search/v1/overview).
