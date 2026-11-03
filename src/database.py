"""DDL과 SQL 실행을 위한 PostgreSQL 연결."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def connect_db() -> psycopg.Connection:
    """with connect_db() as conn: 사용 시 성공하면 commit, 실패하면 rollback."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    url = os.getenv("SUPABASE_DB_URL", "").strip()
    if not url:
        raise RuntimeError("루트 .env에 SUPABASE_DB_URL을 설정하세요.")
    return psycopg.connect(url, sslmode="require", connect_timeout=10, prepare_threshold=None)
