"""Trip 스키마 → JSON Schema 내보내기 (프론트 TS 타입 생성용).

사용:
    uv run python scripts/export_schema.py
    # → schema/trip.schema.json 생성. 프론트에서:
    npx json-schema-to-typescript@15.0.4 -i ../schema/trip.schema.json -o src/lib/trip.gen.ts

스키마를 바꾸면 이 스크립트를 다시 돌리고 두 파일을 같이 커밋한다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.schema.trip import Trip  # noqa: E402

OUT = ROOT / "schema" / "trip.schema.json"


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    schema = Trip.model_json_schema(mode="serialization")
    OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
