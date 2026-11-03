"""Tie each published dimension score to one valid judge run with identical scores."""
import json

from src.scoring.verify import DIMS, LEVELS


def matching_runs(scores, runs):
    """Return the earliest valid exact-match run per dimension; fail closed otherwise."""
    chosen = {}
    for dim in DIMS:
        target = tuple(scores["dimensions"][dim][level] for level in LEVELS)
        matches = [r for r in runs if r["report"].get(dim, {}).get("valid")
                   and tuple(r["output"]["dimensions"][dim][level] for level in LEVELS) == target]
        if not matches:
            raise ValueError(f"No valid run explains {dim} {target}")
        chosen[dim] = min(matches, key=lambda r: r["run_index"])
    return chosen


def snapshot_runs(place_id, run_dir):
    runs = []
    for path in sorted(run_dir.glob(f"{place_id}_run*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        runs.append({"run_index": raw["run_index"], "run_id": raw.get("run_id"),
                     "output": raw["output"], "report": raw["verify"]})
    return runs


def explanations(scores, runs):
    chosen = matching_runs(scores, runs)
    return {dim: {"run_index": run["run_index"], "run_id": run.get("run_id"),
                  "route": run["output"].get("representative_route"),
                  "rationale": run["output"]["dimensions"][dim].get("rationale"),
                  "evidence_ids": run["output"]["dimensions"][dim].get("evidence_ids", []),
                  "lower_conditions": run["output"]["dimensions"][dim].get("lower_conditions", []),
                  "upper_conditions": run["output"]["dimensions"][dim].get("upper_conditions", [])}
            for dim, run in chosen.items()}
