import json
from pathlib import Path

import pytest

from src.scoring.package_difficulty import calculate_package
from src.scoring.visit_modes import build_modes, load_modes
from src.scoring.verify import DIMS, WEIGHTS, round_half_up


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_rebuilds_from_verified_v22_snapshot():
    scores = json.loads((ROOT / "data/scoring/scores_v2.json").read_text(encoding="utf-8"))
    catalog = load_modes()
    assert catalog == build_modes(scores, ROOT / "data/scoring/judge/v2")
    assert len(catalog) == 15
    for place_id, place in catalog.items():
        assert set(place["modes"]) == {"standard", "short", "full"}
        assert place["modes"]["standard"]["score"] == scores[place_id]["composite"]["typical"]
        for mode in place["modes"].values():
            dims = mode["dimensions"]
            assert set(dims) == set(DIMS)
            assert all(1 <= dims[d]["score"] <= 10 and dims[d]["evidence_ids"] for d in DIMS)
            assert mode["score"] == round_half_up(sum(WEIGHTS[d] * dims[d]["score"] for d in DIMS) / 9)
            assert dims["heat"]["level"] == dims["crowd"]["level"] == "typical"


def test_marble_mountain_elevator_and_package_change():
    catalog = load_modes()
    mountain = catalog["dad-02"]["modes"]
    assert mountain["standard"]["score"] == 6  # v2.2 (v2.1: 7)
    assert mountain["short"]["score"] == 5
    assert mountain["full"]["score"] == 7
    # v2.2: site facts come from cited web pages, not fact:* rows
    climb_ids = mountain["short"]["dimensions"]["climb"]["evidence_ids"]
    assert any(i.startswith("http") for i in climb_ids)
    assert not any(i.startswith("fact:") for i in climb_ids)
    days = [[{"place_id": "dad-01", "mode": "standard"}, {"place_id": "dad-02", "mode": "full"}],
            [{"place_id": "dad-03", "mode": "standard"}, {"place_id": "dad-14", "mode": "standard"}]]
    before = calculate_package(days, catalog)
    assert [d["difficulty"] for d in before["days"]] == [8, 4]
    assert (before["peak"], before["mean"]) == (8, 6.0)
    days[0][1]["mode"] = "short"
    after = calculate_package(days, catalog)
    assert [d["difficulty"] for d in after["days"]] == [6, 4]
    assert (after["peak"], after["mean"]) == (6, 5.0)


def test_consecutive_bonus_cap_and_invalid_days():
    catalog = load_modes()
    day = [{"place_id": "dad-01", "mode": "standard"}] * 4
    assert calculate_package([day], catalog)["days"][0]["consecutive_bonus"] == 2
    with pytest.raises(ValueError):
        calculate_package([], catalog)
    with pytest.raises(ValueError):
        calculate_package([[]], catalog)
