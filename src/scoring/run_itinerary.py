"""Score an explicitly mapped itinerary JSON without API or DB access."""
import argparse
import json
from pathlib import Path

from src.scoring.itinerary import evaluate_itinerary
from src.scoring.visit_modes import load_modes


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("itinerary", type=Path, help="JSON object with a days array")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    data = json.loads(args.itinerary.read_text(encoding="utf-8"))
    result = evaluate_itinerary(data["days"], load_modes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"peak={result['peak']} mean={result['mean']} status={result['status']}")


if __name__ == "__main__":
    main()
