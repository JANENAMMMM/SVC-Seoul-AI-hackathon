"""Supabase (Postgres) access for ScoringAI v2.

Safety: this module only ever creates/reads/writes tables whose name starts with
``scoring_``. No DROP / TRUNCATE / ALTER statements exist here.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "scoring_"


def load_env(path=ROOT / ".env"):
    """Tiny .env parser; never prints values."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def connect():
    import psycopg

    load_env()
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL missing")
    # prepare_threshold=None: safe behind Supabase pgbouncer/pooler
    return psycopg.connect(url, autocommit=True, prepare_threshold=None)


DDL = {
    "scoring_places": """
        id text primary key, name_ko text, name_en text, lat double precision,
        lng double precision, google_place_id text, tripadvisor_url text,
        meta jsonb, updated_at timestamptz default now()""",
    "scoring_evidence": """
        id text primary key, place_id text, dimension text, basis text, metric text,
        value jsonb, unit text, text text, source text, source_url text, caveat text,
        updated_at timestamptz default now()""",
    "scoring_reviews": """
        id text primary key, place_id text, source text, lang text, date text,
        trip_type text, rating double precision, text text""",
    "scoring_web_cache": """
        id text primary key, place_id text, query text, url text, title text,
        excerpt text, fetched_at timestamptz default now()""",
    "scoring_judgments": """
        run_id text primary key, place_id text, model text, rubric_version text,
        run_index int, output_json jsonb, citations_valid boolean,
        usage jsonb, created_at timestamptz default now()""",
    "scoring_scores": """
        place_id text, rubric_version text, dimensions jsonb,
        composite_typical int, composite_lower int, composite_upper int,
        grade_display text, confidence text, status text, conditions_json jsonb,
        updated_at timestamptz default now(), primary key (place_id, rubric_version)""",
}


def _check(table):
    if not table.startswith(PREFIX) or table not in DDL:
        raise ValueError(f"refusing to touch non-scoring table: {table}")


def list_public_tables(conn):
    rows = conn.execute(
        "select table_name from information_schema.tables "
        "where table_schema='public' order by table_name").fetchall()
    return [r[0] for r in rows]


def ensure_schema(conn):
    for table, cols in DDL.items():
        _check(table)
        conn.execute(f"create table if not exists {table} ({cols})")


def _adapt(v):
    from psycopg.types.json import Jsonb

    return Jsonb(v) if isinstance(v, (dict, list)) else v


JSONB_COLS = {"value", "meta", "output_json", "usage", "dimensions", "conditions_json"}


def upsert(conn, table, rows, key=("id",)):
    _check(table)
    if not rows:
        return 0
    from psycopg.types.json import Jsonb

    cols = list(rows[0].keys())
    sets = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in key)
    sql = (f"insert into {table} ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))}) "
           f"on conflict ({', '.join(key)}) do update set {sets}")
    data = [tuple(Jsonb(r[c]) if c in JSONB_COLS and r[c] is not None else r[c] for c in cols)
            for r in rows]
    with conn.cursor() as cur:
        cur.executemany(sql, data)
    return len(rows)


def query(conn, sql, params=()):
    """Read helper; caller must only reference scoring_ tables."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        names = [d.name for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]


def count(conn, table):
    _check(table)
    return conn.execute(f"select count(*) from {table}").fetchone()[0]


def dumps(o):
    return json.dumps(o, ensure_ascii=False, default=str)
