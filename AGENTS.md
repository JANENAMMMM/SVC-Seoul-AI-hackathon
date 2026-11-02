# 에이전트 작업 안내

## 기본 규칙

- 실행·설정은 `README.md`, 브랜치·커밋·PR 규칙은 `CONTRIBUTING.md`를 따릅니다.
- 기존 작업과 `legacy/`는 요청 없이 수정하지 않습니다.
- 실행한 확인 결과를 보고하고, 실행하지 않은 작업을 성공했다고 표현하지 않습니다.

## DB 사용

- 데이터 API: `src.supabase_client.get_supabase()` 사용.
- SQL 및 테이블 생성·변경·삭제: `src.database.connect_db()`를 `with` 문으로 사용.
- 접속 정보는 루트 `.env`에서 읽습니다. 변수 이름은 `.env.example`을 참고합니다.
- 키·비밀번호·접속 URI는 출력하거나 커밋하지 않습니다.
- 서버용 Secret key는 RLS를 우회하므로 사용자별 권한은 API에서 확인합니다. 공용 클라이언트로 사용자 세션을 변경하지 않습니다.
- SQL 값은 파라미터로, 동적 테이블·컬럼 이름은 `psycopg.sql.Identifier`로 전달합니다.

## DB 변경

- 작업 전 실제 DB 구조와 기존 SQL 파일을 확인하고, 요청된 범위만 변경합니다.
- 구조·권한 변경은 `supabase/migrations/YYYYMMDDHHMMSS_설명.sql`에 남깁니다. 디렉터리가 없으면 생성합니다.
- 적용한 SQL 파일은 수정하지 않고 후속 파일을 추가합니다. 다른 기능에 미치는 영향은 PR에 적습니다.
- 기존 공유 데이터나 테이블을 삭제하려면 명시적인 요청이 필요합니다. 테스트는 직접 만든 테이블·데이터만 정리합니다.
- Git으로 코드를 되돌려도 DB는 복구되지 않습니다.

```bash
uv run python scripts/db.py run supabase/migrations/파일명.sql
uv run python scripts/db.py smoke-test
uv run pytest
```

`run`은 기본 트랜잭션에서 SQL을 실행하지만 적용 이력을 추적하지 않습니다.
중복 적용 여부를 확인하고 실행하세요. `smoke-test`도 실제 DB를 변경한 뒤 정리합니다.
변경 후 실제 DB 상태와 관련 동작을 확인하고 결과를 보고하세요.
