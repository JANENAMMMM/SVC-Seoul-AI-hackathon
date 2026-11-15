# 심사용 제출본

반걸음은 관광지의 보행·계단·더위·혼잡 근거를 평가하고, 부모님 조건에 맞춰 여행 동선을 구성합니다. 고객은 변경안을 확인하고 승인한 일정을 부모님에게 공유할 수 있습니다.

## 빠른 실행

Python 3.10 이상, uv, Node.js와 npm이 필요합니다.

```bash
uv sync
npm --prefix frontend ci
npm --prefix frontend run build
uv run uvicorn api.main:app --host 127.0.0.1 --port 8131
```

http://localhost:8131 에서 시연 데이터를 이용한 화면을 볼 수 있습니다. 시연에는 API 키나 DB 설정이 필요하지 않습니다. 지도 타일과 웹 폰트는 네트워크를 사용합니다.

실제 DB 조회·저장과 모델 채점은 별도 설정이 필요합니다. `.env.example`을 참고해 심사 환경의 `.env`를 구성하세요. 기존 키나 운영 데이터를 제출본에 넣지 않습니다. 실제 연결의 범위와 권한, DB 마이그레이션 절차는 `docs/ui-redesign.md`를 참고하세요.

## 코드 안내

- `src/scoring/`: 자료 수집·근거 연결·관광지 평가·검수 승인
- `src/planner/`: 조건 반영·일정 구성·식당 배치·변경안
- `src/profile/`: 부모님 프로필과 보행 조건
- `api/`: 프로필·평가·일정·공유 API
- `frontend/`: 고객·운영자·부모님 화면
- `tests/`: 백엔드 회귀 검증
- `supabase/migrations/`: DB 구조와 권한 변경 SQL

채점 스냅샷은 공개 장소 평가 자료입니다. 사용자 여행·세션·비밀 설정은 포함하지 않습니다. 원문 수집 캐시와 실제 DB는 제공하지 않으므로 재수집·실시간 근거 조회에는 환경 설정이 필요합니다. 식당 수집 파일이 없는 경우 실제 일정 엔진의 식당 추천은 제한됩니다.

## 제출본 생성

저장소에서 검토한 커밋을 지정해 실행합니다. 기존 목적지는 덮어쓰지 않습니다.

```bash
uv run python scripts/export_submission.py ~/bangeoreum-submission --revision HEAD
```

다른 작업 디렉터리의 공개 채점 자료를 사용할 때는 `--data-root /경로/data`를 지정합니다. Git 추적 파일 중 실행 코드·테스트·기능 문서·최종 발표 자료를 복사하고, 필요한 로컬 채점 JSON을 추가합니다. Git 이력, 개발 규칙, 인계 문서, 과거 구현, 설치 디렉터리, `.env`는 복사하지 않습니다. 파일별 SHA-256과 코드 커밋은 `SUBMISSION.json`에 기록합니다. 실행 전 선택한 공개 JSON에 비밀값이나 개인 데이터가 없는지 검토하세요.

```bash
uv run pytest
```

이 명령은 백엔드를 검증합니다. DB smoke-test와 실제 재채점은 별도 작업이며 제출본 생성 명령이 실행하지 않습니다.
