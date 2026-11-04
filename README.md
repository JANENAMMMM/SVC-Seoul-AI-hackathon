# 반걸음 백엔드

## 새 UI 실행

운영자 평가 근거 → 고객 동선 조정·승인 → 부모님 공유를 연결한 새 UI는 `frontend/`에 있습니다. 실행·권한·실제 연동과 시연 데이터의 차이는 [UI 재설계 안내](docs/ui-redesign.md)를 참고하세요. 기존 목업은 그대로 유지합니다.

## 목업 실행

날짜·가족 인원·부모님 프로필을 입력하고, 여러 날의 일정과 지도·전후 비교·여행 카드를 체험하는 목업입니다. 상단의 MD 작업실에서는 장소를 끌어 놓거나 버튼으로 예시 일정을 편집하고 고객 미리보기를 확인합니다. 별도 API 키 없이 실행하며, 장소·거리·항공·숙소는 시연용 예시입니다. 자세한 내용은 [목업 안내](docs/mockup.md)를 참고하세요.

```bash
uv run python mockup/serve.py
```

접속: http://localhost:8129/mockup/

## 로컬 실행

```bash
uv sync
cp .env.example .env
# .env에 Supabase 프로젝트 URL과 서버용 Secret key 입력
uv run uvicorn api.main:app --reload
```

API 문서: http://localhost:8000/docs

## Supabase 연결

Supabase 대시보드에서 프로젝트 URL과 서버용 Secret key를 확인하고
루트 `.env`의 `SUPABASE_URL`, `SUPABASE_SECRET_KEY`에 입력합니다.
배포 환경에서는 같은 이름의 환경변수를 설정합니다.
`.env`는 Git에서 제외되며, Secret key는 백엔드에서만 사용합니다.
이 키는 RLS를 우회하므로 사용자별 접근 권한은 API에서 확인해야 합니다.

공용 클라이언트는 최초 호출 시 생성하고 재사용합니다.
설정이 없어도 `/health`와 기본 서버는 실행됩니다.
키를 바꿨다면 서버를 다시 시작하세요.

```python
from src.supabase_client import get_supabase

db = get_supabase()
# 실제로 생성한 테이블 이름으로 변경
result = db.table("your_table").select("*").limit(10).execute()
```

FastAPI의 동기 라우트(`def`)에서는 `Depends(get_supabase)`로 주입할 수도 있습니다.
이 클라이언트는 서버 공용이므로 사용자 로그인이나 세션 변경에 사용하지 마세요.
테이블과 데이터 모델은 각 기능에서 별도로 정의합니다.
클라이언트 생성만으로 DB 연결이 검증되지는 않으며, 실제 테이블 조회로 확인합니다.

## 테스트

테이블 생성·변경·삭제는 PostgreSQL 연결을 사용합니다.
Supabase의 **Connect → Session pooler → URI**를 복사해
루트 `.env`의 `SUPABASE_DB_URL`에 넣으세요. `[YOUR-PASSWORD]`에는
프로젝트 DB 비밀번호를 입력합니다(API Secret key와 다름).
비밀번호에 `@`, `:`, `/` 같은 문자가 있으면 URI에 넣을 때 percent encoding이 필요합니다.

```bash
# 임시 테이블 생성 → 구조 변경 → 데이터 CRUD → 테이블 삭제
uv run python scripts/db.py smoke-test

# 임의의 SQL 파일 실행 (성공 시 commit, 실패 시 rollback)
uv run python scripts/db.py run path/to/migration.sql
```

이 명령은 개발자 터미널용이며 HTTP API로 노출하지 않습니다.

```bash
uv run pytest
```
