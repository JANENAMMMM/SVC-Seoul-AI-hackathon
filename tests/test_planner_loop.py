import datetime
import json

from pydantic import TypeAdapter

from src.planner.edit import refine
from src.planner.engine import build_itinerary
from src.planner.schema import EditCommand, PlanRequest
from src.planner.sources import Restaurants, load_restaurants
from tests.conftest import _hours, _restaurant

IDS = [f"dad-{i:02d}" for i in (1, 2, 3, 5, 6, 7, 8, 14)]
adapter = TypeAdapter(EditCommand)
STRONG = {"age": 55, "gender": "male"}


def cmds(*items):
    return [adapter.validate_python(i) for i in items]


def base_plan(profile, restaurants, ids=IDS, days=4):
    req = PlanRequest(travelers=[profile], place_ids=ids, days=days, start_date=datetime.date(2026, 12, 7))
    return build_itinerary(req, restaurants)


def meal_ids(it):
    return {(d.day, s.meal): s.restaurant.place_id for d in it.days for s in d.stops
            if s.type == "meal" and s.restaurant}


def day_of(it):
    return {s.place_id: d.day for d in it.days for s in d.stops if s.type == "attraction"}


# ------------------------------------------------------------ meal_pins

def test_every_picked_restaurant_is_pinned_except_fixed_ones(make_profile, restaurants):
    it = base_plan(make_profile(), restaurants)
    pinned = it.state.meal_pins
    assert pinned and all(":" in k for k in pinned)
    for (day, meal), pid in meal_ids(it).items():
        fixed = any(s.fixed for s in it.days[day - 1].stops if s.type == "meal" and s.meal == meal)
        assert fixed or pinned[f"{day}:{meal}"] == pid
    assert not any(pid.endswith("buffet") for pid in pinned.values())


def test_untouched_days_keep_their_restaurants_after_a_move(make_profile, restaurants):
    before = base_plan(make_profile(), restaurants)
    after = refine(before, cmds({"op": "move_place", "place_id": "dad-05", "day": 2}), rest=restaurants).itinerary
    south = day_of(before)["dad-03"]
    banahills = day_of(before)["dad-01"]
    for day in (south, banahills):
        assert {k: v for k, v in meal_ids(before).items() if k[0] == day} == \
               {k: v for k, v in meal_ids(after).items() if k[0] == day}


def test_stale_pins_are_dropped_when_a_slot_disappears(make_profile, restaurants):
    before = base_plan(make_profile(), restaurants)
    after = refine(before, cmds({"op": "remove_place", "place_id": "dad-14"}), rest=restaurants).itinerary
    assert set(after.state.meal_pins) == {f"{d}:{m}" for (d, m) in meal_ids(after)
                                         if not any(s.fixed for s in after.days[d - 1].stops
                                                    if s.type == "meal" and s.meal == m)}


# ------------------------------------------------------------ swap_restaurant

def test_swap_replaces_only_that_meal_and_excludes_the_old_restaurant(make_profile, restaurants):
    before = base_plan(make_profile(), restaurants)
    old_id = meal_ids(before)[(1, "lunch")]
    res = refine(before, cmds({"op": "swap_restaurant", "day": 1, "meal": "lunch"}), rest=restaurants)
    after = res.itinerary
    new_ids = meal_ids(after)
    assert not res.clarification
    assert new_ids[(1, "lunch")] != old_id and old_id in after.state.excluded_restaurants
    assert old_id not in new_ids.values()
    untouched = {k: v for k, v in meal_ids(before).items() if k != (1, "lunch")}
    assert all(new_ids[k] == v for k, v in untouched.items() if k in new_ids)
    assert "1일차 점심" in res.change_summary and "→" in res.change_summary


def test_swap_can_be_repeated_without_picking_an_excluded_restaurant(make_profile, restaurants):
    first = refine(base_plan(make_profile(), restaurants),
                   cmds({"op": "swap_restaurant", "day": 1, "meal": "lunch"}), rest=restaurants).itinerary
    second = refine(first, cmds({"op": "swap_restaurant", "day": 1, "meal": "lunch"}), rest=restaurants)
    picked = meal_ids(second.itinerary)[(1, "lunch")]
    assert picked not in second.itinerary.state.excluded_restaurants[:-1] + [meal_ids(first)[(1, "lunch")]]
    assert len(set(second.itinerary.state.excluded_restaurants)) == 2


def test_swap_on_fixed_or_missing_meal_asks_back(make_profile, restaurants):
    before = base_plan(make_profile(), restaurants)
    banahills_day = day_of(before)["dad-01"]
    res = refine(before, cmds({"op": "swap_restaurant", "day": banahills_day, "meal": "lunch"}), rest=restaurants)
    assert "바꿀 식당이 없습니다" in res.clarification and res.itinerary.plan_id == before.plan_id
    out_of_range = refine(before, cmds({"op": "swap_restaurant", "day": 9, "meal": "lunch"}), rest=restaurants)
    assert "9일차" in out_of_range.clarification


def test_swap_without_alternative_keeps_the_plan(make_profile, tmp_path):
    only = _restaurant("dad-05", "only", "유일한 식당", "vietnamese_restaurant", 4.8, 500, 16.0617, 108.2469,
                       hours=_hours())
    path = tmp_path / "one.json"
    path.write_text(json.dumps({"attractions": [{"attraction": {"id": "dad-05"}, "restaurants": [only]}]},
                               ensure_ascii=False), encoding="utf-8")
    rest = load_restaurants(path)
    before = base_plan(make_profile(), rest, ids=["dad-05"], days=1)
    assert meal_ids(before)[(1, "lunch")] == "dad-05-only"
    res = refine(before, cmds({"op": "swap_restaurant", "day": 1, "meal": "lunch"}), rest=rest)
    assert "대체할 다른 식당 후보" in res.clarification
    assert res.itinerary.plan_id == before.plan_id and not res.applied_commands


def test_pin_is_ignored_when_restaurant_is_no_longer_usable(make_profile, restaurants):
    before = base_plan(make_profile(), restaurants)
    req = before.request.model_copy(deep=True)
    req.state.meal_pins["1:lunch"] = "does-not-exist"
    rebuilt = build_itinerary(req, restaurants)
    assert meal_ids(rebuilt)[(1, "lunch")] != "does-not-exist"


# ------------------------------------------------------------ adjust_walk_limit

def limit_of(it):
    return max(d.max_continuous_walk_min for d in it.days)


def test_adjust_more_steps_up_one_bucket_and_restores_standard_mode(make_profile):
    profile = make_profile(**STRONG, walking_duration="15_30min")
    before = build_itinerary(PlanRequest(travelers=[profile], place_ids=["dad-02"], days=1), Restaurants())
    assert next(s for s in before.days[0].stops if s.type == "attraction").mode == "short"
    res = refine(before, cmds({"op": "adjust_walk_limit", "direction": "more"}), rest=Restaurants())
    after = res.itinerary
    assert after.state.walk_limit_override == 40 and "20분 → 40분" in res.change_summary
    assert next(s for s in after.days[0].stops if s.type == "attraction").mode == "standard"
    assert any("40분으로 조정" in a for a in after.assumptions)


def test_adjust_less_lowers_limit_and_adds_rests(make_profile):
    profile = make_profile(**STRONG, walking_duration="over_2hour")
    before = build_itinerary(PlanRequest(travelers=[profile], place_ids=["dad-03"], days=1), Restaurants())
    res = refine(before, cmds({"op": "adjust_walk_limit", "direction": "less"}), rest=Restaurants())
    assert res.itinerary.state.walk_limit_override == 60
    assert limit_of(res.itinerary) <= 60
    rests = lambda it: sum(s.type == "rest" for d in it.days for s in d.stops)
    assert rests(res.itinerary) >= rests(before)


def test_adjust_walk_limit_can_be_chained(make_profile):
    profile = make_profile(**STRONG, walking_duration="30_60min")
    plan = build_itinerary(PlanRequest(travelers=[profile], place_ids=["dad-03"], days=1), Restaurants())
    one = refine(plan, cmds({"op": "adjust_walk_limit", "direction": "more"}), rest=Restaurants()).itinerary
    two = refine(one, cmds({"op": "adjust_walk_limit", "direction": "more"}), rest=Restaurants())
    assert one.state.walk_limit_override == 60 and two.itinerary.state.walk_limit_override == 90
    third = refine(two.itinerary, cmds({"op": "adjust_walk_limit", "direction": "more"}), rest=Restaurants())
    assert "이미 가장 높은 단계(90분)" in third.clarification


def test_adjust_less_at_the_lowest_bucket_asks_back(make_profile):
    profile = make_profile(**STRONG, walking_duration="under_15min")
    plan = build_itinerary(PlanRequest(travelers=[profile], place_ids=["dad-05"], days=1), Restaurants())
    res = refine(plan, cmds({"op": "adjust_walk_limit", "direction": "less"}), rest=Restaurants())
    assert "이미 가장 낮은 단계(12분)" in res.clarification


def test_pace_factor_applies_on_top_of_the_adjusted_limit(make_profile):
    profile = make_profile(**STRONG, walking_duration="30_60min")
    plan = build_itinerary(PlanRequest(travelers=[profile], place_ids=["dad-03"], days=1), Restaurants())
    res = refine(plan, cmds({"op": "adjust_walk_limit", "direction": "more"}, {"op": "set_pace", "pace": "slower"}),
                 rest=Restaurants())
    assert res.itinerary.state.walk_limit_override == 60
    assert limit_of(res.itinerary) <= 45


def test_new_commands_work_through_the_api():
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as client:
        profile = client.post("/api/profile", json={"age": 55, "gender": "male", "walking_duration": "15_30min"}).json()
        plan = client.post("/api/planner/plan", json={"travelers": [profile], "place_ids": ["dad-02"], "days": 1}).json()
        res = client.post("/api/planner/refine", json={
            "itinerary": plan, "commands": [{"op": "adjust_walk_limit", "direction": "more"}]})
        assert res.status_code == 200
        assert res.json()["itinerary"]["state"]["walk_limit_override"] == 40
