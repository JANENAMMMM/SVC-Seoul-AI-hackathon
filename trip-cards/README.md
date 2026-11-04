# 부모님용 여행 일정 카드

한 박(하루)당 1080×1350 PNG 한 장. 사진과 텍스트만 바꿔 끼우는 템플릿입니다.

```bash
uv run --with playwright python scripts/render_trip_cards.py [입력.json] [출력폴더]
```

- 기본 입력 `trip-cards/sample.json`(예시 데이터), 기본 출력 `trip-cards/out/`
- `photo`는 `assets/place-photos/<슬러그>/NN.jpg`. 작가·라이선스는 같은 폴더의 `credits.json`에서 읽어 카드 상단에 표기합니다.
- 글씨 기준: 본문 34px 이상, 장소명 50px, 시간 44px. 정보는 한 줄에 하나씩.

## 사진 (`assets/place-photos/`)

Wikimedia Commons의 CC0·CC BY·CC BY-SA·퍼블릭 도메인 가로 사진만 수집(`scripts/collect_place_photos.py`).
CC BY 계열이므로 사용 시 작가 표기 필수. 여행지별 10장 목표였으나 껌탄 코코넛 마을 1장, 누이탄타이 온천 2장만 확보했습니다(Commons에 자료 부족).
