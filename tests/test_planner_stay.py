import json
from pathlib import Path

from src.planner.stay import level_by_rule, load_config, resolve_stay, stay_minutes

PROFILE = Path(__file__).resolve().parents[1] / "src" / "planner" / "attraction_profile.json"


def test_manual_value_wins_over_rule():
    place = {"types": ["Beach"], "stay_level": "long", "stay_source": "manual_estimate"}
    assert resolve_stay(place) == ("long", "manual_estimate")


def test_new_place_uses_type_default():
    assert resolve_stay({"types": ["Museum"]}) == ("brief", "type:Museum")


def test_ignored_and_unknown_types_fall_back():
    level, source = resolve_stay({"types": ["Tourist attraction", "Tour operator"]})
    assert (level, source) == ("half", "fallback")
    assert resolve_stay({"types": []}) == ("half", "fallback")


def test_first_mapped_type_is_used():
    place = {"types": ["Tourist attraction", "Water park", "Beach"]}
    assert resolve_stay(place) == ("long", "type:Water park")


def test_long_walk_raises_level_but_is_capped():
    config = load_config()
    assert level_by_rule({"types": ["Beach"], "walk_min": 95}, config) == ("half", "type:Beach+walk")
    assert level_by_rule({"types": ["Theme park"], "walk_min": 95}, config)[0] == "long"


def test_minutes_follow_config():
    assert stay_minutes("brief") == 60
    assert stay_minutes("long") == 240


def test_profile_has_valid_levels_for_all_places():
    config = load_config()
    places = json.loads(PROFILE.read_text(encoding="utf-8"))["places"]
    assert len(places) == 15
    for pid, place in places.items():
        level, _ = resolve_stay(place, config)
        assert level in config["levels"], pid
