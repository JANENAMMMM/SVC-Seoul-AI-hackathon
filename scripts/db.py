"""SQL 파일 실행 및 테이블 생성/수정/삭제 연결 테스트."""

import argparse
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.database import connect_db


def smoke_test() -> None:
    # 모든 변경을 한 트랜잭션에서 처리해 실패 시에도 테스트 테이블을 남기지 않는다.
    table = sql.Identifier("public", "connection_smoke_" + uuid4().hex)
    with connect_db() as conn:
        conn.execute(sql.SQL("CREATE TABLE {} (id integer PRIMARY KEY, message text NOT NULL)").format(table))
        conn.execute(sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(table))
        conn.execute(sql.SQL("ALTER TABLE {} ADD COLUMN checked boolean DEFAULT false").format(table))
        conn.execute(sql.SQL("INSERT INTO {} (id, message) VALUES (%s, %s)").format(table), (1, "hello"))
        conn.execute(sql.SQL("UPDATE {} SET checked = true WHERE id = %s").format(table), (1,))
        row = conn.execute(sql.SQL("SELECT message, checked FROM {} WHERE id = %s").format(table), (1,)).fetchone()
        if row != ("hello", True):
            raise RuntimeError("테스트 데이터가 예상과 다릅니다.")
        conn.execute(sql.SQL("DELETE FROM {} WHERE id = %s").format(table), (1,))
        conn.execute(sql.SQL("DROP TABLE {}").format(table))
    print("테이블 생성/구조 변경, 데이터 입력/수정/조회/삭제, 테이블 삭제 성공")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("smoke-test")
    run = commands.add_parser("run")
    run.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "smoke-test":
            smoke_test()
        else:
            statement = args.file.read_text(encoding="utf-8")
            with connect_db() as conn:
                conn.execute(statement)
            print("SQL 파일 실행 완료")
    except psycopg.Error as exc:
        # 드라이버 오류 원문에는 접속 정보가 포함될 수 있다.
        print(f"DB 실행 실패: {type(exc).__name__} (SQLSTATE: {exc.sqlstate or '없음'}). 접속 설정과 SQL을 확인하세요.", file=sys.stderr)
        raise SystemExit(1) from None
    except (RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
