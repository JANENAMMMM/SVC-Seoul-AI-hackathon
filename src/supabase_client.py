"""서버 전용 Supabase 클라이언트. FastAPI에서는 Depends(get_supabase)로 사용."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client


@lru_cache
def get_supabase() -> Client:
    """최초 사용 시 설정을 읽는다. 환경변수는 루트 .env보다 우선한다."""
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    names = ("SUPABASE_URL", "SUPABASE_SECRET_KEY")
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(
            "Supabase 설정이 필요합니다: " + ", ".join(missing)
            + ". .env.example을 참고해 루트 .env를 작성하세요."
        )
    return create_client(values["SUPABASE_URL"], values["SUPABASE_SECRET_KEY"])
