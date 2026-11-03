# 관광지 체력 부담 측정: 선행연구·표준·데이터셋 (50+ 여행자, 3단계 난이도 근거)

## 1. 관광지 내부 GPS/궤적 연구와 공개 데이터셋

### Takeaway
테마파크·동물원·생태공원 방문객을 GPS로 추적한 연구는 있다. 다만 시설 안에서 걸은 거리를 숫자로 보고한 사례는 드물고(확인된 것은 생태공원 평균 1,209m 하나), 동남아 관광지 대상의 공개 궤적 데이터셋은 찾지 못했다.

### Cited Findings
- PortAventura(스페인) 테마파크 방문객의 시공간 궤적을 GPS로 기록하고, 방문객 활동 패턴을 이해하는 데 '시간'이 중요하다고 보고(Birenboim 외, 2013) — [HUJI Urban Vitality Lab 출판 목록](https://urban-vitality-lab.huji.ac.il/publications?page=1)
- Ocean Park(홍콩)에서 GPS 추적과 설문을 함께 사용. 방문객은 시간의 약 26%를 식사·쇼핑·이동 같은 '일상적' 활동에 썼다(Ji, Zhao, Wang, Huang 2021) — [Oxford Brookes RADAR PDF](https://radar.brookes.ac.uk/radar/file/f9075378-efe9-47f9-bf62-61c94c00bc98/1/Spatiotemporal%20behaviour%20of%20theme%20park%20visitors%20-%202021%20-%20Ji%20Zhao%20Wang%20Huang.pdf)
- 다마 동물공원(도쿄): 위치 기록만으로는 전시별 체류 시간을 추정하기 어렵고, 보행 속도가 핵심 변수였다 — [Kawase·Kurata·Yabe, ENTER 2012](https://www.comp.tmu.ac.jp/kurata/research/JKawaseYKurataNYabe-ENTER12.pdf); [Theory and Applications of GIS 24(1)](https://doi.org/10.5638/thagis.24.1)
- Vinhais 생태공원(포르투갈): 추적 방문객의 평균 이동거리는 1,209m(학회 논문) — [IPB Biblioteca Digital](https://bibliotecadigital.ipb.pt/entities/publication/5a3ebf49-b2a7-41d0-a4c0-761221855d8a/full)
- 홍콩 Pokfulam 컨트리파크: GPS 내장 PDA로 추적했고, 조사 시간대와 위치에 따라 GPS 수신 품질이 달라졌다 — [Journal of Park and Recreation Administration](https://js.sagamorepub.com/index.php/jpra/article/view/1387)

### Inferences
- 방문객 궤적 데이터를 직접 얻기는 어렵다. 그래서 해커톤에서는 'OSM 보행로망/지도에서 잰 시설 내부 경로 길이 ÷ 고령자 보행 속도'로 대신 추정하는 방식이 현실적이다. Kawase 연구가 보행 속도를 핵심 변수로 본 것도 이 방식의 근거가 된다.
- Ocean Park에서 이동 등에 쓴 시간이 약 26%라는 결과는 '시설 안 이동·대기 시간'을 부담 요소로 넣는 근거로 인용할 수 있다.

### Gaps
- 다낭·방콕·발리 관광지 내부의 공개 GPS 궤적 데이터셋은 찾지 못했다.
- 테마파크 1일 보행거리를 직접 수치로 제시한 피어리뷰 논문은 이번 검색 범위에서 확인하지 못했다.

## 2. 여행 중 걸음 수·웨어러블 연구 (고령 여행자)

### Takeaway
여행 중 고령자의 걸음 수를 가속도계로 직접 잰 관광 연구는 찾지 못했다. 대신 인용할 수 있는 것은 고령자 일상 걸음 수 기준치와, 심박·걸음 수로 관광 피로를 측정한 일본 연구다.

### Cited Findings
- 일본 연구: 심박수와 걸음 수를 객관적 피로 지표로 썼다. 안전한 환경에서의 관광 활동은 정신적 피로보다 '보행에 따른 신체 피로'로 주로 인식된다고 주장 — [Sensors and Materials SM3318](https://sensors.myu-group.co.jp/sm_pdf/SM3318.pdf)
- 관광에서 보행은 기본 활동이지만 여행 중에는 기차·차량도 자주 쓴다는 점을 다룬 일본 논문 — [Sensors and Materials SM1188](https://sensors.myu-group.co.jp/sm_pdf/SM1188.pdf)
- 한국 고령자의 가속도계 일일 걸음 수 성·연령별 백분위 기준 — [서울시립대 Pure](https://pure.uos.ac.kr/en/publications/normative-percentile-curves-of-accelerometer-measured-daily-step-/)
- 대만 고령자의 경우, 하루 중·고강도 활동 30분이 남성 약 8,600보, 여성 약 8,900보에 해당 — [Frontiers in Public Health 2025](https://www.frontiersin.org/articles/10.3389/fpubh.2025.1575209/full)
- 소비자용 활동량계는 고령자에게 대체로 정확하고 신뢰도가 있었다(소표본 파일럿) — [IJESAB](https://digitalcommons.wku.edu/ijesab/vol11/iss5/8)

### Inferences
- '관광지 1곳에서 추정한 걸음 수(경로 길이 ÷ 보폭)'를 고령자 일상 기준치(예: 약 5,000~9,000보)와 비교하면 3단계 컷오프를 설명하기 쉽다. 단, 이 컷오프 값은 팀이 정하는 설계값이다.

### Gaps
- 관광지 1곳당 고령 여행자 걸음 수를 실측한 연구는 찾지 못했다.

## 3. 기존 난이도 등급 체계와 접근성 인증

### Takeaway
3단계 등급의 근거로 인용하기 가장 좋은 것은 호주 AS 2156.1/AWTGS다. 등급 1~5를 노면, 폭, 경사, 거리, 계단으로 정의한다. SAC T1~T6, Intrepid 1~5도 같은 구조(낮은 단계 = 정비된 평지)를 보여준다. 접근성 인증(VisitEngland/AccessAble, Reisen für Alle)은 등급을 매기지 않고 측정값을 기술하는 방식이다.

### Cited Findings
- AS 2156.1-2001(R2018) 「Walking tracks – Part 1: Classification and signage」: 관리기관에 보행로 분류와 표지 기준을 제공하는 표준(유료) — [Standards Australia](https://store.standards.org.au/product/as-2156-1-2001); [NZ Codehub](https://codehub.building.govt.nz/resources/as-2156-1-2001)
- AWTGS는 보행로를 5등급으로 나눈다. 거리는 1~3등급에서만 등급에 영향을 준다 — [NSW National Parks](https://www.nationalparks.nsw.gov.au/safety/bushwalking-safety/australian-walking-track-grading-system); [Bushwalking Australia](https://www.bushwalkingaustralia.org/walkers-info/walking-track-grading-system)
- 1등급(2차 자료 기준): 폭 1,200mm 이상의 넓은 포장로로 휠체어 이용 가능. 휠체어 최대 경사 1:14(7.14%) 언급. 2등급은 폭 1,200mm 미만 정비로이며 일부 장애물 있음 — [Trail Hiking AU](https://www.trailhiking.com.au/preparation/australian-walking-track-grading-system-awtgs/); [Tasmania AS2156 Track Classes PDF](https://listdata.thelist.tas.gov.au/public/AS2156_Track_Classes.pdf). 원문 표준과 대조하지는 못했다.
- NSW 정책: 보행 위주 다목적 트랙도 AS 2156에 따라 설계·분류해야 한다 — [NSW Environment](https://www.environment.nsw.gov.au/topics/parks-reserves-and-protected-areas/park-policies/walking-tracks)
- SAC 산악·고산 하이킹 스케일 T1~T6(2002 도입). T1은 잘 정비된 길이고 추락 위험이 없다. T2는 부분적으로 가파른 연속 등산로. T4부터 길이 없는 구간이 있고 손을 써야 한다. 좋은 날씨를 전제로 평가하며, 2023년에 개정되었다 — [SAC 영문 PDF(Avegno)](https://www.avegnogordevio.ch/files/Berg-Alpinwanderskala-EN.pdf); [OSM Key:sac_scale](https://wiki.openstreetmap.org/wiki/Key:sac_scale)
- Intrepid Travel 신체 등급 1~5: 1 = 휴식형, 신체적으로 힘든 활동 없음. 2 = 쉬운 활동 일부, 준비 불필요. 3 = 심박이 오르는 중간 강도, 좋은 체력 필요. 4 = 대부분 도전적. 5 = 극한 조건과 고강도. 정성적 정의만 있다 — [Intrepid Physical ratings](https://www.intrepidtravel.com/us/about/physical-rating)
- VisitEngland 접근성 가이드: AccessAble의 'Your Accessibility Guide'로 제작한다. 측량사가 가이드형 또는 현장 평가를 거쳐 수백 개 항목(치수·사진 포함)을 기술한다. 점수제가 아니다 — [VisitBritain](https://www.visitbritain.org/visitengland-joins-forces-accessable-promote-new-tourism-accessibility-guides); [VisitBritain: update accessibility information](https://visitbritain.org/business-advice/make-your-business-accessible-and-inclusive/update-accessibility-information)
- Reisen für Alle(독일): 장애인 단체와 관광 단체가 함께 만든 품질 기준이 있고, 훈련된 조사원이 측정·평가하는 자율 인증이다 — [Factsheet EN PDF](https://www.reisen-fuer-alle.de/local/media/downloads/qualitaetskriterien-rfa/Factsheet-Tourism-for-all-Feb-2021_EN.pdf); [Charts EN PDF](https://reisen-fuer-alle.de/local/media/downloads/qualitaetskriterien-rfa/Charts-englWebsite-Reisen-fuer-alle-EN.pdf). 2023 독일 연방의회 문서에 재정·운영 문제가 언급되어 있다 — [Bundestag](https://www.bundestag.de/resource/blob/1001360/3c63d112b5bf98bbbdba8559ad7baa16/53-15-11-2023-Anlagenkonvolut.pdf)

### Inferences
- 3단계 매핑 제안: 저 = AWTGS 1~2 / SAC T1 / Intrepid 1~2(평탄 포장로, 짧은 거리), 중 = AWTGS 3 / Intrepid 3(경사·계단 일부), 고 = AWTGS 4 이상 / SAC T2 이상 / Intrepid 4 이상(지속 경사, 다수 계단, 비포장). 이 매핑은 팀의 해석이며 공식 대응표가 아니다.
- 기준 항목(노면, 폭, 경사, 거리, 계단)은 OSM 태그(surface, incline, highway=steps, sac_scale)와 경로 길이로 일부 재현할 수 있다.

### Gaps
- Parks Canada, NPS, Paths for All(UK), Disney/Universal 접근성 가이드, TUR4all, G Adventures, Viator의 구체적 기준은 이번 조사에서 1차 출처로 확인하지 못했다.
- AS 2156.1 원문의 수치 기준(등급별 경사·계단 수)은 유료라서 직접 대조하지 못했다.

## 4. 고령 관광객의 피로·신체 제약과 그 원인이 되는 관광지 속성

### Takeaway
고령 관광객 제약 연구는 보행 거리, 계단, 엘리베이터 부재, 신체·건강 한계를 반복해서 핵심 장벽으로 꼽는다. 다만 더위, 대기, 휴식 공간 같은 속성별 효과 크기를 정량화한 연구는 찾지 못했다.

### Cited Findings
- 파루 공항에서 고령 관광객 851명 조사(알가르브): 평소 대중교통을 거의 이용하지 않는 이유가 보행 곤란(34.3%), 계단 오르기 곤란(32.6%)과 주로 관련. 과도한 계단과 엘리베이터 부족이 이용 회피 요인 — [IJTDI 4(2) 163-178](https://iieta.org/journals/ijtdi/paper/10.2495/TDI-V4-N2-163-178)
- 시니어 관광 체계적 문헌고찰(31편, 1980~2025): 주요 장벽은 신체·건강 한계, 재정, 심리적 두려움, 인프라 문제 — [ensani.ir 초록](https://ensani.ir/fa/article/636543/senior-tourism-in-global-perspective-a-systematic-review-ofmotivations-preferences-and-constraints)
- Journal of Travel Research: 나이가 들면 제약 요인의 우선순위가 바뀌고, 이 때문에 패키지 투어 같은 '안전한' 선택으로 옮겨 간다 — [MetaTOC: Seniors' travel constraints and their coping strategies](https://metatoc.com/papers/36856-seniors-travel-constraints-and-their-coping-strategies)
- 2026 미국 설문(상업 후원): 37%가 공항의 긴 보행을 힘들어하고, 19%가 통증이나 피로를 겪는다 — [WDBJ7](https://www.wdbj7.com/2026/10/14/physical-hurdles-keep-older-travelers-grounded-despite-health-benefits/)

### Inferences
- '보행 거리'와 '계단 유무·수'를 1차 가중 요소로 두는 것은 문헌 근거가 가장 강하다. 더위, 대기, 휴식 공간은 보조 요소로 두는 편이 정당화하기 쉽다.

### Gaps
- 대기·줄서기·혼잡과 고령자 피로의 정량 관계, 휴식 공간 밀도의 효과는 1차 연구를 찾지 못했다.

## 5. 혼잡/대기 측정과 덥고 습한 기후의 열스트레스 지수(UTCI, WBGT, PET)

### Takeaway
UTCI는 표준 열스트레스 구간(26~32°C 중등도, 32~38°C 강함, 38°C 초과 매우 강함)이 있어 3단계 보정에 쓰기 좋다. 고령 관광객 전용 동남아 임계값은 없다. 혼잡은 Google 'Popular times'가 사실상 유일한 공개 신호인데, 공식 API가 없다.

### Cited Findings
- UTCI 스트레스 구간(Błażejczyk 외 2013): 9.1~26.0°C 스트레스 없음, 26.1~32.0°C 중등도 열스트레스, 32.1~38.0°C 강한 열스트레스, 38.1°C 이상 매우 강한 열스트레스 — [Geographia Polonica PDF](https://www.rcin.org.pl//Content/194928/PDF/WA51_229606_r2021-t94-no2_G-Polonica-Pecelj.pdf)
- 홍콩 고령자의 열 쾌적 범위는 UTCI 20~25°C(관광 연구 아님) — [PolyU 학위논문](https://theses.lib.polyu.edu.hk/handle/200/12146)
- 구랑위(중국) 관광객·주민의 최대 수용 UTCI는 약 29~30°C — [Land 13(6):864, 2024](https://mdpi-res.com/d_attachment/land/land-13-00864/article_deploy/land-13-00864.pdf?version=1718445774)
- 싱가포르 고령자는 젊은 층보다 녹지·건축 환경 특성에 더 민감하다(PET 기반 현장실험) — [PMC8410920](https://pmc.ncbi.nlm.nih.gov/articles/PMC8410920)
- 동남아 UTCI/WBGT 미래 전망: 대륙부(태국, 캄보디아, 미얀마)는 최성수기에 하루 6~9시간 심한 열스트레스 — [Scientific Reports 2025](https://link.springer.com/10.1038/s41598-025-28817-6)
- 싱가포르 열스트레스 권고(2023.7, WBGT 기반 3단계 저/중/고). 저 = WBGT 31°C 미만 — [Malay Mail](https://malaymail.com/news/singapore/2023/07/24/singapores-first-heat-stress-advisory-launched-as-temperatures-keep-rising-amid-climate-change/81534)
- ISO 7243:2017 WBGT 기준은 순응 여부만 반영하고, 고령자 등 취약군 임계값은 반영하지 않는다(2024 체계적 고찰) — [Int J Biometeorology 2024](https://link.springer.com/article/10.1007/s00484-024-02783-6)
- Google Popular times·대기시간·체류시간: Location History에 동의한 사용자의 익명 집계 데이터이고 차분 프라이버시를 적용한다. 방문이 충분한 장소에만 표시된다 — [Google 지원](https://support.google.com/maps/answer/11323117?hl=en-IN)

### Inferences
- 실외 관광지는 '방문 시간대 UTCI ≥ 32°C(강한 열스트레스)'면 한 단계 올리는 규칙이 방어하기 쉽다. 다낭·방콕은 공개 재분석 자료(ERA5-HEAT 등)나 기상 API로 계산할 수 있다(가능성 추정이며 미검증).
- 싱가포르의 WBGT 3단계 체계는 '3단계'라는 구조 자체를 정당화하는 참고 사례로 쓸 수 있다.
- 'Popular times'는 공식 API가 없으므로 수작업으로 기록하는 정도가 현실적이다(10~20곳이면 가능).

### Gaps
- 싱가포르 WBGT의 중·고 구간 경계값, 태국과 베트남의 공식 열지수 구간은 확인하지 못했다.
- 관광지 대기열을 측정한 학술 연구는 이번 조사에서 확보하지 못했다.

## 6. 에너지 소비 프레이밍: 2024 Adult Compendium MET

### Takeaway
2024 Adult Compendium의 보행 항목은 매우 느린 산책 2.3 MET부터 계단 오르기 4.5 MET까지 있어서 '저/중/고'를 MET 구간으로 설명할 수 있다. 'sightseeing' 전용 코드는 보행 항목에 없다.

### Cited Findings (모두 [pacompendium.com/walking](https://pacompendium.com/walking/))
- 17151 매우 느린 산책(평지): 2.3 MET
- 17152 느린 보행 2.0~2.4 mph: 2.8 MET
- 17170 평지 2.5 mph: 3.0 MET
- 17160 즐기기 위한 보행(walking for pleasure): 3.5 MET
- 17190 보통 속도 2.8~3.4 mph: 3.8 MET
- 17070 계단 내려가기: 3.5 MET
- 17133 계단 오르기(느린 속도): 4.5 MET
- 17032 매우 느린 오르막(경사 5~20%): 5.0 MET / 17034 경사 1~5%, 보통~빠른 속도: 5.3 MET
- Compendium 대분류 목록 — [pacompendium.com/adult-compendium](https://pacompendium.com/adult-compendium/)

### Inferences
- 제안 매핑(팀 설계): 저 = 주로 평지 산책(2.3~3.0 MET) / 중 = 지속 보행, 내리막 계단(3.5~3.8 MET) / 고 = 계단 오르기, 오르막(4.5 MET 이상). 'MET × 시간'으로 관광지별 부담 점수를 계산할 수 있다.
- 고령자는 최대 유산소 능력이 낮아서 같은 MET라도 상대 강도가 더 높다는 점을 감안해야 한다(일반 생리학 지식이며 이번 조사에서 출처를 확보하지 못함).

### Gaps
- 서 있기(standing) 코드와 관광(touring) 관련 코드는 보행 페이지에 없다. 다른 대분류(예: Inactivity, Miscellaneous)를 확인해야 한다.
- 공식 인용 형식: Herrmann SD 외, 2024, J Sport Health Sci. 이번 조사에서 직접 확인하지는 못했다.
