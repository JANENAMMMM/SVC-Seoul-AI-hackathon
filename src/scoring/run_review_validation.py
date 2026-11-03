"""CLI for review labels collected after scoring; no API or DB access."""
import argparse
import csv
import json
from pathlib import Path

from src.scoring.review_validation import validate_annotations
from src.scoring.visit_modes import load_modes


ROOT = Path(__file__).resolve().parents[2]


def used_tripadvisor_reviews():
    for path in (ROOT / "data/scoring/raw/tripadvisor").glob("dad-*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for review in data.get("reviews", []):
            yield ("tripadvisor", str(review.get("id", "")), review.get("text", ""))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("annotations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with args.annotations.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    report = validate_annotations(rows, load_modes(), used_tripadvisor_reviews())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(report['comparisons'])} dimension comparisons; {len(report['excluded'])} reused reviews excluded")


if __name__ == "__main__":
    main()
