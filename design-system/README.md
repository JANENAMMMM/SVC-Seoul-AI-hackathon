# 반걸음 디자인 시스템

웹 화면에 사용할 디자인 토큰과 React 19 컴포넌트입니다.

## 미리보기

저장소 루트에서 실행한 뒤 http://localhost:8127/preview.html 을 엽니다.
미리보기의 상품과 가격은 예시이며 API는 연결하지 않습니다.

```bash
uv run python -m http.server 8127 --bind 127.0.0.1 --directory design-system
```

## 사용 및 수정

- `tokens.json`: 색·간격·글꼴·반경. 변경 후 `uv run python design-system/sync_tokens.py` 실행
- `styles.css`: 공통 스타일과 화면 테마를 함께 불러오는 진입점. 화면에서 import하고 `bg-ui` 클래스 하위에 적용
- `components.css`: 공통 컴포넌트 기본 스타일
- `theme.css`: 확정한 화면 스타일. `components.css` 다음에 불러옵니다. 데스크톱 컨트롤은 4px, 모바일은 8px 모서리를 사용합니다.
- `components/index.tsx`: 컴포넌트와 속성 타입. 사용 예시는 `preview.html` 참고
- 모바일 하단 메뉴 사용 시 페이지 하단에 메뉴 높이만큼 여백 확보

타입 검사에는 Node.js와 npm이 필요합니다.

```bash
cd design-system
npm ci
npm run typecheck
```
