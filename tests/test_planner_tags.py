"""희윤님 식당 태그(venue_type, ingredient_tags, tag_confidence, tag_evidence) 반영 검증. 태그가 없으면 기존 동작."""

import datetime
import json

from src.planner.engine import build_itinerary
from src.planner.schema import PlanRequest
from src.planner.sources import load_restaurants
from tests.conftest import ROOT, _restaurant


def _file(tmp_path, items):
    attractions = json.loads((ROOT / "data" / "scoring" / "attractions.json").read_text(encoding="utf-8"))
    a = next(x for x in attractions if x["id"] == "dad-05")
    blocks = [{"attraction": {"id": "dad-05"},
               "restaurants": [_restaurant("dad-05", k, f"식당 {k}", "vietnamese_restaurant", rating, 300,
                                           a["lat"] + .001 * i, a["lng"] + .001 * i)
                               | extra for i, (k, rating, extra) in enumerate(items)]}]
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"attractions": blocks}, ensure_ascii=False), encoding="utf-8")
    return load_restaurants(path)


def _chosen(profile, rest):
    req = PlanRequest(travelers=[profile], place_ids=["dad-05"], days=1, start_date=datetime.date(2026, 12, 7))
    it = build_itinerary(req, rest)
    return it, [s.restaurant for d in it.days for s in d.stops if s.type == "meal" and s.restaurant]


ITEMS = [
    ("pork", 5.0, {"ingredient_tags": ["pork"], "tag_confidence": "high", "tag_evidence": ["#3 '돼지고기 국물'"]}),
    ("street", 4.9, {"venue_type": "street_food", "ingredient_tags": [], "tag_confidence": "low"}),
    ("plain", 4.5, {"venue_type": "restaurant", "ingredient_tags": []}),
]


def test_without_preferences_every_tagged_restaurant_is_allowed(make_profile, tmp_path):
    _, picks = _chosen(make_profile(), _file(tmp_path, ITEMS))
    assert "dad-05-pork" in {p.place_id for p in picks}  # 하루 두 끼 중 가장 점수 높은 식당이 선택된다


def test_avoided_ingredient_tag_excludes_the_restaurant(make_profile, tmp_path):
    rest = _file(tmp_path, ITEMS)
    _, picks = _chosen(make_profile(avoid_ingredients=["pork"]), rest)
    assert picks and all(p.place_id != "dad-05-pork" for p in picks)


def test_restaurant_only_venue_excludes_street_food(make_profile, tmp_path):
    rest = _file(tmp_path, ITEMS)
    _, picks = _chosen(make_profile(venues=["restaurant"]), rest)
    assert picks and all(p.venue_type != "street_food" for p in picks)


def test_unknown_venue_type_is_not_filtered(make_profile, tmp_path):
    rest = _file(tmp_path, [("a", 4.9, {"venue_type": "unknown"}), ("b", 4.5, {})])
    _, picks = _chosen(make_profile(venues=["restaurant"]), rest)
    assert "dad-05-a" in {p.place_id for p in picks}  # 장소 유형을 모르는 식당도 거르지 않는다


def test_old_data_without_tags_keeps_working_and_warns(make_profile, tmp_path):
    rest = _file(tmp_path, [("a", 4.9, {}), ("b", 4.5, {})])
    it, picks = _chosen(make_profile(avoid_ingredients=["pork"]), rest)
    assert picks and picks[0].ingredient_tags is None
    assert any("재료 태그가 없어" in a for a in it.assumptions)


def test_tagged_data_warns_that_missing_tag_is_not_proof(make_profile, tmp_path):
    it, _ = _chosen(make_profile(avoid_ingredients=["pork"]), _file(tmp_path, ITEMS))
    assert any("태그가 없다고" in a for a in it.assumptions)
    assert not any("재료 태그가 없어" in a for a in it.assumptions)


def test_pick_exposes_tag_fields_for_explanations(make_profile, tmp_path):
    _, picks = _chosen(make_profile(), _file(tmp_path, ITEMS))
    first = next(p for p in picks if p.place_id == "dad-05-pork")
    assert first.ingredient_tags == ["pork"] and first.tag_confidence == "high" and first.tag_evidence


def test_couple_venues_use_the_common_choice(make_profile, tmp_path):
    rest = _file(tmp_path, ITEMS)
    both = [make_profile(venues=["restaurant"]), make_profile(venues=["street_food", "restaurant"])]
    req = PlanRequest(travelers=both, place_ids=["dad-05"], days=1, start_date=datetime.date(2026, 12, 7))
    picks = [s.restaurant for d in build_itinerary(req, rest).days for s in d.stops if s.type == "meal" and s.restaurant]
    assert picks and all(p.venue_type != "street_food" for p in picks)


def test_korean_slot_uses_is_korean_final_when_present(make_profile, tmp_path):
    # 최종 판정만 있는 파일, 원본(is_korean)과 판정이 엇갈리는 파일 모두 is_korean_final을 따른다.
    only_final = _file(tmp_path, [("a", 4.9, {"is_korean_final": False}), ("b", 4.5, {"is_korean_final": True})])
    profile = make_profile(korean_need="daily")
    _, picks = _chosen(profile, only_final)
    assert any(p.place_id == "dad-05-b" and p.is_korean for p in picks)
    assert not any(p.place_id == "dad-05-a" and p.is_korean for p in picks)

    disagree = _file(tmp_path, [("a", 4.9, {"is_korean": True, "is_korean_final": False}),
                                ("b", 4.5, {"is_korean": False, "is_korean_final": True})])
    _, picks = _chosen(profile, disagree)
    korean_picks = [p for p in picks if p.is_korean]
    assert korean_picks and all(p.place_id == "dad-05-b" for p in korean_picks)


def test_old_files_without_is_korean_final_still_use_is_korean(make_profile, tmp_path):
    rest = _file(tmp_path, [("a", 4.9, {"is_korean": False}), ("b", 4.5, {"is_korean": True})])
    _, picks = _chosen(make_profile(korean_need="daily"), rest)
    assert any(p.place_id == "dad-05-b" and p.is_korean for p in picks)
