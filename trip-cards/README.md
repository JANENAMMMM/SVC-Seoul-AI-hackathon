# 부모님용 여행지 소개 카드

여행지 1곳당 1080×1350 PNG 한 장. 상단은 여행지 사진과 "n일차 ①(그날 몇 번째)" 배지, 하단은 시간·장소·설명과 **전체 여행 동선(세로)** 입니다. 현재 장소만 굵게, 나머지는 흐리게 표시합니다.

```bash
uv run --with playwright python scripts/render_trip_cards.py [입력.json] [출력폴더]
```

- 기본 입력 `trip-cards/sample.json`(예시 데이터 12곳), 기본 출력 `trip-cards/out/`
- 입력 형식: `days[].stops[]`에 `time`, `place`, `desc`, `photo`(`assets/place-photos/<슬러그>/NN.jpg`)
- 사진 작가·라이선스는 `credits.json`에서 읽어 카드에 자동 표기합니다.
- 동선이 12곳을 넘으면 현재 위치 앞뒤만 보여주고 나머지는 "⋮ 앞/뒤 N곳"으로 접습니다.
- 글씨 기준: 장소명 62px(현재 동선 46px), 설명 36px, 동선 36px, 시간 30px 이상.

## 사진 (`assets/place-photos/`)

Wikimedia Commons의 CC0·CC BY·CC BY-SA·퍼블릭 도메인 가로 사진만 수집(`scripts/collect_place_photos.py`).
CC BY 계열이므로 사용 시 작가 표기 필수. 여행지별 10장 목표였으나 껌탄 코코넛 마을 1장, 누이탄타이 온천 2장만 확보했습니다(Commons에 자료 부족).
