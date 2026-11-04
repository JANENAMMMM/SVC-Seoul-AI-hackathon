import datetime

from pydantic import TypeAdapter

from src.planner.edit import NO_LLM_MESSAGE, refine
from src.planner.engine import build_itinerary
from src.planner.schema import EditCommand, PlanRequest
from src.planner.sources import Restaurants

IDS = [f"dad-{i:02d}" for i in (1, 2, 3, 5, 6, 7, 8, 14)]
adapter = TypeAdapter(EditCommand)


def base_plan(profile):
    req = PlanRequest(travelers=[profile], place_ids=IDS, days=4, start_date=datetime.date(2026, 12, 7))
    return build_itinerary(req, Restaurants())


def cmds(*items):
    return [adapter.validate_python(i) for i in items]


def day_of(it):
    return {s.place_id: d.day for d in it.days for s in d.stops if s.type == "attraction"}


def stops_signature(day):
    return [(s.type, s.start, s.end, s.place_id) for s in day.stops]


def test_move_place_changes_only_affected_days(make_profile):
    before = base_plan(make_profile())
    res = refine(before, cmds({"op": "move_place", "place_id": "dad-05", "day": 2}), rest=Restaurants())
    after = res.itinerary
    assert day_of(after)["dad-05"] == 2
    assert not res.clarification and "미케 해변" in res.change_summary
    south = [d for d in before.days if any(s.place_id == "dad-03" for s in d.stops)][0].day
    assert stops_signature(before.days[south - 1]) == stops_signature(after.days[south - 1])


def test_remove_and_add_place(make_profile):
    before = base_plan(make_profile())
    removed = refine(before, cmds({"op": "remove_place", "place_id": "dad-06"}), rest=Restaurants()).itinerary
    assert "dad-06" not in day_of(removed)
    added = refine(removed, cmds({"op": "add_place", "place_id": "dad-09", "day": 1}), rest=Restaurants()).itinerary
    assert day_of(added)["dad-09"] == 1


def test_set_mode_is_applied(make_profile):
    before = base_plan(make_profile(age=55, gender="male", walking_duration="over_2hour"))
    res = refine(before, cmds({"op": "set_mode", "place_id": "dad-02", "mode": "short"}), rest=Restaurants())
    stop = next(s for d in res.itinerary.days for s in d.stops if s.place_id == "dad-02")
    assert stop.mode == "short"


def test_lighten_day_sets_short_modes_and_does_not_raise_difficulty(make_profile):
    before = base_plan(make_profile(age=55, gender="male", walking_duration="over_2hour"))
    day = day_of(before)["dad-02"]
    res = refine(before, cmds({"op": "lighten_day", "day": day}), rest=Restaurants())
    after_day = res.itinerary.days[day - 1]
    assert all(s.mode == "short" for s in after_day.stops if s.type == "attraction")
    assert after_day.difficulty <= before.days[day - 1].difficulty
    assert "'엘리베이터·사원 일부'" in res.change_summary and "짧은 관람" not in res.change_summary


def test_more_korean_meals_upgrades_need_and_set_pace_changes_state(make_profile):
    before = base_plan(make_profile(korean_need="occasional"))
    res = refine(before, cmds({"op": "more_korean_meals"}, {"op": "set_pace", "pace": "slower"}), rest=Restaurants())
    assert res.itinerary.state.korean_need_override == "every_2_3_days"
    assert res.itinerary.state.pace == "slower"
    assert len(res.applied_commands) == 2


def test_invalid_command_changes_nothing_and_asks_back(make_profile):
    before = base_plan(make_profile())
    res = refine(before, cmds({"op": "move_place", "place_id": "dad-05", "day": 9},
                              {"op": "remove_place", "place_id": "dad-06"}), rest=Restaurants())
    assert res.clarification and "9일차" in res.clarification
    assert res.itinerary.plan_id == before.plan_id and not res.applied_commands


def test_feedback_without_commands_explains_llm_is_not_connected(make_profile):
    res = refine(base_plan(make_profile()), [], feedback="너무 힘들어요", rest=Restaurants())
    assert res.clarification == NO_LLM_MESSAGE


def test_refine_is_repeatable_from_the_returned_state(make_profile):
    first = refine(base_plan(make_profile()), cmds({"op": "move_place", "place_id": "dad-05", "day": 2}),
                   rest=Restaurants()).itinerary
    second = refine(first, cmds({"op": "set_pace", "pace": "slower"}), rest=Restaurants()).itinerary
    assert day_of(second)["dad-05"] == 2
