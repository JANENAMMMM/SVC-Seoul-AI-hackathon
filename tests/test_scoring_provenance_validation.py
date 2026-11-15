import json
from pathlib import Path

import pytest

from src.scoring.itinerary import evaluate_itinerary
from src.scoring.provenance import explanations, snapshot_runs
from src.scoring.review_validation import validate_annotations
from src.scoring.visit_modes import load_modes
from src.scoring import run_judge


ROOT = Path(__file__).resolve().parents[1]


def test_every_published_dimension_has_exact_valid_explanation():
    scores = json.loads((ROOT / "data/scoring/scores_v2.json").read_text(encoding="utf-8"))
    catalog = load_modes()
    for place_id, score in scores.items():
        source = explanations(score, snapshot_runs(place_id, ROOT / "data/scoring/judge/v2"))
        for dim, item in source.items():
            assert item["evidence_ids"]
            assert catalog[place_id]["modes"]["standard"]["dimensions"][dim]["source_run_id"] == item["run_id"]


def test_no_exact_valid_explanation_fails_closed():
    score = {"dimensions": {d: {"typical": 5, "lower": 4, "upper": 7}
                            for d in ("climb", "walking", "heat", "crowd")}}
    run = {"run_index": 1, "report": {d: {"valid": True} for d in score["dimensions"]},
           "output": {"dimensions": {d: {"typical": 6, "lower": 4, "upper": 7}
                                     for d in score["dimensions"]}}}
    with pytest.raises(ValueError, match="No valid run explains"):
        explanations(score, [run])


def test_review_validation_excludes_reused_review_and_counts_only_observed_dimensions():
    catalog = load_modes()
    rows = [
        {"place_id": "dad-02", "mode": "short", "source": "tripadvisor", "review_id": "old",
         "source_url": "https://example.org/old", "review_text": "old review", "climb": "5"},
        {"place_id": "dad-02", "mode": "short", "source": "google", "review_id": "new",
         "source_url": "https://example.org/new", "review_text": "stairs remained after the elevator",
         "climb": "6", "walking": ""},
    ]
    report = validate_annotations(rows, catalog, [("tripadvisor", "old", "old review")])
    assert len(report["excluded"]) == 1
    result = report["comparisons"][0]
    assert (result["dimension"], result["n"], result["within_1"], result["status"]) == (
        "climb", 1, 1, "insufficient")
    assert len(report["comparisons"]) == 1


def test_itinerary_requires_route_evidence_and_flags_review_place():
    catalog = load_modes()
    with pytest.raises(ValueError, match="Route evidence required"):
        evaluate_itinerary([[{"place_id": "dad-02", "mode": "short"}]], catalog)
    result = evaluate_itinerary([[{"place_id": "dad-07", "mode": "standard",
                                   "source_ref": "sample itinerary p2", "route_note": "market visit"}]], catalog)  # v2.2 needs_review site
    assert result["status"] == "needs_review" and result["review_required"] == ["dad-07"]


def test_existing_score_cannot_be_replaced_by_accidental_single_run(monkeypatch):
    class ExistingScores:
        def exists(self):
            return True

        def read_text(self, encoding):
            return '{"dad-02": {}}'

    monkeypatch.setattr(run_judge, "SCORES", ExistingScores())
    monkeypatch.setattr(run_judge.db, "connect", lambda: pytest.fail("must not connect"))
    with pytest.raises(SystemExit):
        run_judge.main(["--sites", "dad-02", "--runs", "1"])


def test_invalid_run_outvoted_by_two_agreeing_runs_is_not_review():
    from src.scoring.verify import DIMS, aggregate
    dim = {"typical": 4, "lower": 3, "upper": 5}
    ok = {d: {"valid": True} for d in DIMS}
    bad = {**ok, "heat": {"valid": False}}
    out = {"dimensions": {d: dict(dim) for d in DIMS}, "confidence": "medium"}
    runs = [{"output": out, "report": bad}, {"output": out, "report": ok}, {"output": out, "report": ok}]
    agg = aggregate(runs)
    assert agg["status"] == "ok" and agg["notes"] == ["heat: 1 invalid run(s)"]
    # only one valid run left -> still needs review
    agg = aggregate([{"output": out, "report": bad}, {"output": out, "report": ok}])
    assert agg["status"] == "needs_review"
