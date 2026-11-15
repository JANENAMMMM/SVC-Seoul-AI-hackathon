# 비(非)Google 합법 데이터 소스: 동남아 관광지 체력 부담 정보

> 조사일: 2026-11-02. 도구 호출 약 15회로 제한된 조사임. 여러 공식 문서(Viator 전체 스펙, Naver 개발자 문서, TAT 포털)는 403 응답이나 fetch 차단 때문에 직접 확인하지 못했고, 해당 내용은 Gaps에 적었다. Overpass 실측도 샌드박스 네트워크 차단(HTTP 000)으로 실패했다.

## Tripadvisor Content API

### Takeaway
레거시 Content API는 더 이상 업데이트되지 않으며 Terra로 이전하라는 안내가 나온다. 위치당 리뷰 5개, 사진 5장만 제공하므로 체력 부담 라벨의 주 소스로 쓰기는 어렵다.

### Cited Findings
- 공식 문서에 "The legacy Tripadvisor Content API is no longer being updated"라고 적혀 있고, Terra(https://docs.terra.tripadvisor.com/)로의 이전을 권장한다 — [Tripadvisor Content API overview](https://tripadvisor-content-api.readme.io/reference/overview)
- 위치 상세(name, address, rating, Tripadvisor URL)와 위치당 최대 5개 리뷰, 5장 사진을 제공한다 — [tripadvisor-content-api.readme.io](https://tripadvisor-content-api.readme.io/)
- (2차 출처) 셀프서브 키, 월 5,000건 무료 후 종량제. 로고, 버블 평점 이미지, 링크백 표시 의무가 있고 TOS 감사로 집행된다고 한다 — [Supergood API Report Card](https://supergood.ai/api-report-card/tripadvisor)

### Inferences
- 리뷰 5개로는 "계단 많음", "경사" 같은 키워드를 통계적으로 뽑기 어렵다. 표시 의무 조항을 보면 파생 점수의 저장이나 가공도 제한될 가능성이 크다(약관 원문 미확인).

### Gaps
- 저장/캐싱 기간, 파생 데이터 사용, 비영리 해커톤 자격에 관한 약관 원문은 확인하지 못했다.
- Terra API의 필드와 접근 조건도 미확인.

## Viator / Klook / KKday / GetYourGuide

### Takeaway
Viator `/products/{product-code}`의 `additionalInfo` 배열과 "Health restrictions and accessibility" 정보는 체력 라벨로 쓸 만한 가장 유망한 정형 소스다. 다만 이번 조사에서 enum 값을 원문으로 확인하지는 못했다.

### Cited Findings
- 구매 전 고객에게 알려야 할 모든 상품 정보는 `/product` 및 보조 엔드포인트에서 제공된다 — [Viator affiliate technical docs](https://docs.viator.com/partner-api/affiliate/technical)(검색 스니펫. 직접 fetch는 403)
- 일괄 수집에는 `/products/modified-since`, 실시간 단건 조회에는 `/products/{product-code}`를 쓴다. 검색 응답에는 모든 필드가 들어 있지 않다 — [Viator Technical Guide](https://partnerresources.viator.com/travel-commerce/technical-guide/)
- `additionalInfo`는 상세 페이지에 반드시 모두 표시해야 하는 조항 배열이다. 로지스틱스 항목에 "Duration", "Health restrictions and accessibility"가 있고, 연령 밴드에 `5 = "Senior"`가 있다 — [APIs.guru Viator spec](https://api.apis.guru/v2/specs/viator.com/1.0.0.json)(구버전 v1 스펙)
- 연동 문의처는 affiliateapi@tripadvisor.com — [Viator partner-api 검색 결과](https://docs.viator.com/partner-api/)

### Inferences
- 학습 데이터 기준으로 v2에는 `additionalInfo[].type` 값으로 `PHYSICAL_EASY`, `PHYSICAL_MEDIUM`, `PHYSICAL_MODERATE`, `PHYSICAL_HARD`, `WHEELCHAIR_ACCESSIBLE`, `NO_HEART_PROBLEMS`, `NO_BACK_PROBLEMS` 같은 값이 있는 것으로 알고 있다. **이번 조사에서 1차 출처로 검증하지 못했으므로** 스펙 offset 100000 이후 부분이나 v2 OpenAPI 파일로 반드시 확인해야 한다.
- 투어 상품 라벨을 "명소" 라벨로 옮기는 데는 무리가 있다. 상품은 이동, 가이드, 여러 명소를 묶은 단위이기 때문이다.

### Gaps
- Klook, KKday, GetYourGuide의 파트너 API 필드와 접근 조건은 조사하지 못했다(호출 한도 소진).
- Viator Basic/Full affiliate 등급별 필드 접근 범위와 rate limit도 미확인.

## 체력 등급을 공개하는 투어 운영사 (Intrepid, G Adventures 등)

### Takeaway
이번 조사에서는 확인하지 못했다.

### Cited Findings
- 없음.

### Inferences
- 일정 단위의 등급(예: 1~5 척도)은 참고 라벨이나 루브릭 설계용으로는 쓸 수 있다. 다만 웹 콘텐츠 저작권이 있으므로 원문 복제보다 "등급 정의 참고" 수준으로 쓰는 편이 안전하다(추론).

### Gaps
- Intrepid "Physical rating", G Adventures "Physical Grading"의 정의 페이지 URL과 이용약관.

## OpenStreetMap / Overpass / Mapillary

### Takeaway
OSM(ODbL)의 계단, 경사, 노면, 휠체어, 벤치, 화장실 태그는 합법적으로 쓸 수 있는 정형 소스이고 상업적 이용도 가능하다(출처 표시와 share-alike 조건). 그러나 다낭 실측 수치는 네트워크 차단으로 얻지 못했다.

### Cited Findings
- `step_count`의 정의는 "Number of individual steps in a stair, part of a stair or on a stile"이다. 2024/12 기준 약 15,000개의 `entrance=*` 노드에 쓰였다 — [OSM Wiki Key:step_count](https://wiki.openstreetmap.org/wiki/Key:step_count)
- 공개 Overpass 인스턴스의 권장 사용량은 하루 약 10,000건, 다운로드 1GB 미만이다. 요청 기본 타임아웃은 180초, 메모리는 512MiB이고, 초과하면 429/504를 반환한다. 매퍼가 아닌 일반 사용자 대상 앱의 백엔드로 쓰려면 자체 인스턴스를 운영해야 한다 — [Overpass API docs: commons](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)

### Inferences
- 해커톤 규모(명소 10~20곳)라면 사전에 한 번 Overpass로 뽑아 정적 파일로 저장하면 정책 안에 충분히 들어간다.
- 다낭 bbox(15.95,108.05,16.15,108.35)를 대상으로 `way["highway"="steps"]`, `["step_count"]`, `nwr["wheelchair"]`, `node["amenity"="bench"]`, `nwr["amenity"="toilets"]`, `way["incline"]` 쿼리를 `out count`로 실행할 것을 권장한다(쿼리는 작성했으나 실행 실패).

### Gaps
- 동남아 도시별 태그 수치(taginfo, Overpass)는 측정하지 못했다.
- Mapillary/KartaView 라이선스, Wheelmap/AccessibilityCloud는 조사하지 못했다.

## 관광청 오픈데이터, Wikidata

### Takeaway
태국 TAT는 API 키 기반 개발자 포털이 있다고 알려져 있지만 1차 문서는 확인하지 못했다. data.go.th에는 TAT 데이터셋이 Open Data Common 라이선스로 올라와 있다.

### Cited Findings
- (2차 출처) TAT Developer Portal이 attractions, events, routes 데이터를 API 키 방식으로 제공한다 — [Thai Open Data MCP (glama.ai)](https://glama.ai/mcp/servers/h2ka1u5qvn)
- TAT 출처의 관광객 행동 데이터셋이 Open Data Common 라이선스로 게시되어 있다 — [data.go.th tourist-behavior](https://dev.data.go.th/en/dataset/tourist-behavior)

### Gaps
- 베트남, 인도네시아 관광청 오픈데이터, Wikidata 속성(P2044 elevation, P2046 area 등)의 커버리지는 미확인.

## YouTube / Naver / Kakao (한국인 여행 콘텐츠)

### Takeaway
YouTube 자막은 Data API로 받을 수 없다(편집 권한 필요). Naver와 Kakao 검색 API는 제목, 요약 snippet, URL만 주므로 본문을 얻으려면 크롤링이 필요하고, 이 경우 약관과 저작권 위험이 생긴다.

### Cited Findings
- `captions.download`는 200 units가 들고 "requires the user to have permission to edit the video"이다. 따라서 타인 영상의 자막은 받을 수 없다 — [YouTube Data API captions.download](https://developers.google.com/youtube/v3/docs/captions/download)
- Kakao(Daum) 검색은 `/v2/search/blog`, `/v2/search/cafe`(page 최대 50, size 최대 50), `/v2/search/vclip`(page 15, size 30)를 제공한다. 응답은 `meta`(`total_count`, `pageable_count`, `is_end`)와 `documents`(title, contents, url, datetime)로 구성되고, `Authorization: KakaoAK {REST_API_KEY}` 헤더가 필요하다 — [Kakao Developers Daum Search](http://developers.kakao.com/docs/en/daum-search/dev-guide)
- (2차 출처) Naver 검색 API는 client ID당 하루 25,000건 무료이고 `/v1/search/blog.json`의 필드는 `title`, `link`, `description`, `bloggername`, `postdate`이다. 검색당 최대 1,000건까지 조회할 수 있고, 키 발급이 NAVER API HUB(ncloud)로 옮겨졌을 가능성이 있다 — [Scrapfly](https://scrapfly.io/blog/posts/how-to-scrape-naver), [Apify maolab](https://apify.com/maolab/naver-search-api)

### Inferences
- snippet(`description`/`contents`)과 vclip의 재생 시간만으로도 "계단", "오르막", "더위" 같은 키워드의 언급 빈도를 셀 수 있다. 원문 저장 없이 집계 지표만 쓰는 방식이 가장 안전하다.

### Gaps
- Naver 공식 문서(developers.naver.com)는 fetch가 차단되어 쿼터와 약관 원문을 확인하지 못했다. Kakao 쿼터 페이지도 미확인.

## 날씨/더위 (Open-Meteo)

### Takeaway
Open-Meteo 무료 API는 비상업 용도로만 쓸 수 있고 CC BY 4.0 라이선스다. 해커톤 시연에는 적합하지만, 광고나 구독이 붙는 서비스로 가면 유료 플랜이 필요하다.

### Cited Findings
- 무료 한도는 하루 10,000건 미만, 시간당 5,000건, 분당 600건, 월 300,000건이다. 비상업 전용이며 구독이나 광고가 있는 앱은 상업적 이용으로 본다. 유료 플랜(Standard, Professional, Enterprise)은 월 1M, 5M, 50M 이상 호출을 제공하고, 데이터는 CC BY 4.0이다 — [Open-Meteo Terms](https://open-meteo.com/en/terms)

### Gaps
- `apparent_temperature`와 UTCI 변수의 제공 여부는 이번에 확인하지 못했다(학습 지식으로는 `apparent_temperature` hourly 변수가 있다. docs 페이지에서 검증 필요).
- 각국 기상청(베트남 NCHMF, 태국 TMD, 인도네시아 BMKG)의 API도 미조사.
