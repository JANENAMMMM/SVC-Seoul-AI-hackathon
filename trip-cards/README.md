# 부모님용 여행지 소개 카드

여행지 1곳당 1080×1350 PNG 한 장. 전면 사진 위에 "n일차 · n번째" 배지, 시간·장소명·설명을 올리고, 하단 시트에 **전체 여행 동선**을 보여줍니다. 현재 장소만 굵게, 나머지는 흐리게 표시합니다.

```bash
uv run --with playwright python scripts/render_trip_cards.py [입력.json] [출력폴더]
```

- 기본 입력 `trip-cards/sample.json`(예시 데이터 12곳), 기본 출력 `trip-cards/out/`
- 입력 형식: `days[].stops[]`에 `time`, `place`, `desc`, `photo`(`assets/place-photos/<슬러그>/NN.jpg`)
- 사진 작가·라이선스는 `credits.json`에서 읽어 카드에 자동 표기합니다.
- `place_vi`(선택): 베트남어 원어를 시간 옆에 병기합니다.
- 동선이 길어 하단 시트를 넘치면 글씨를 28px까지 줄입니다(그 이상은 미대응).
- 글씨 기준: 장소명 104px(세리프), 설명 40px, 동선 35px(최소 28px).

## 사진 (`assets/place-photos/`)

Wikimedia Commons의 CC0·CC BY·CC BY-SA·퍼블릭 도메인 가로 사진만 수집(`scripts/collect_place_photos.py`).
CC BY 계열이므로 사용 시 작가 표기 필수. 여행지별 10장 목표였으나 껌탄 코코넛 마을 1장, 누이탄타이 온천 2장만 확보했습니다(Commons에 자료 부족).
