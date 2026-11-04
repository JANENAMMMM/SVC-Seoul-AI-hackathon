"""UI schema inspection/application. Connection details are never printed."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.database import connect_db

MIGRATION = Path(__file__).resolve().parents[1] / "supabase/migrations/20261104210000_ui_sharing.sql"
TABLES = ("ui_trips", "ui_proposals", "ui_shares", "ui_opinions")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "apply"])
    args = parser.parse_args()
    try:
        with connect_db() as conn:
            rows = conn.execute("select table_name,column_name,data_type from information_schema.columns "
                                "where table_schema='public' and (table_name like 'ui_%%' or table_name='scoring_feedback') "
                                "order by table_name,ordinal_position").fetchall()
            if args.action == "inspect":
                for row in rows:
                    print(" | ".join(row))
                return
            existing = {r[0] for r in rows} & set(TABLES)
            if existing:
                print("UI tables already exist; refusing duplicate/partial application: " + ", ".join(sorted(existing)))
                raise SystemExit(1)
            conn.execute(MIGRATION.read_text(encoding="utf-8"))
            print("UI migration applied in one transaction.")
    except Exception as exc:
        print("Database operation failed: " + type(exc).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
