"""하루 구성(compose): 피로 예산, 균형, 한식 전체 조건, 식당 중복 금지, 불가능할 때의 안내."""

import datetime
import math

import pytest

from src.planner.compose import ComposeUnsupported, compose_days
from src.planner.engine import _build_ctx, build_itinerary, select_modes
from src.planner.profile_merge import merge_profiles
from src.planner.schema import PlanRequest, PlanState
from src.planner.sources import Restaurants, load_places, load_settings

MONDAY = datetime.date(2026, 12, 7)
CITY4 = ["dad-05", "dad-06", "dad-07", "dad-08"]
CITY6 = ["dad-02", "dad-05", "dad-06", "dad-07", "dad-08", "dad-09"]
PLACES = load_places()


def plan(profile, ids, days, rest=None, state=None, travelers=None):
    req = PlanRequest(travelers=travelers or [profile], place_ids=ids, days=days, start_date=MONDAY,
                      state=PlanState(**(state or {})))
    return build_itinerary(req, rest if rest is not None else Restaurants())


def attractions(day):
    return list(dict.fromkeys(s.place_id for s in day.stops if s.type == "attraction"))


def day_fatigue(day):
    return sum(PLACES[p].modes[m]["score"] for p, m in {(s.place_id, s.mode) for s in day.stops if s.type == "attraction"})


# ── 피로 예산 ───────────────────────────────────────────────

@pytest.mark.parametrize("duration,expected", [("under_15min", 9), ("15_30min", 11), ("30_60min", 13),
                                               ("1_2hour", 15), ("over_2hour", 17)])
def test_fatigue_budget_follows_walking_duration(make_profile, duration, expected):
    p = merge_profiles([make_profile(age=65, walking_duration=duration)], PlanState(), load_settings())
    assert p.fatigue_budget == expected


def test_fatigue_budget_is_lowered_by_age_and_the_weakest_traveler_decides(make_profile):
    st = load_settings()
    old = merge_profiles([make_profile(age=78, walking_duration="30_60min")], PlanState(), st)
    assert old.fatigue_budget == 12                      # 75세 이상 -1
    couple = merge_profiles([make_profile(age=65, walking_duration="1_2hour"),
                             make_profile(age=65, walking_duration="under_15min")], PlanState(), st)
    assert couple.fatigue_budget == 9                    # 가장 낮은 값
    slower = merge_profiles([make_profile(age=65, walking_duration="30_60min")], PlanState(pace="slower"), st)
    assert slower.fatigue_budget < 13                    # 천천히 하면 예산도 줄어든다


def test_fatigue_budget_follows_the_walk_limit_command(make_profile):
    st = load_settings()
    base = merge_profiles([make_profile(age=65, walking_duration="30_60min")], PlanState(), st)
    more = merge_profiles([make_profile(age=65, walking_duration="30_60min")], PlanState(walk_limit_override=60), st)
    assert more.fatigue_budget > base.fatigue_budget


@pytest.mark.parametrize("duration", ["under_15min", "15_30min", "30_60min", "1_2hour"])
def test_no_day_exceeds_the_fatigue_budget(make_profile, duration):
    profile = make_profile(age=65, walking_duration=duration)
    budget = merge_profiles([profile], PlanState(), load_settings()).fatigue_budget
    it = plan(profile, CITY6 + ["dad-03"], 4)
    assert all(day_fatigue(d) <= budget for d in it.days), [day_fatigue(d) for d in it.days]


def test_shortened_course_is_used_to_stay_within_budget(make_profile):
    profile = make_profile(age=65, walking_duration="under_15min")      # 예산 9
    it = plan(profile, ["dad-02", "dad-05", "dad-06"], 1)                # 표준으로는 6+4+3=13
    day = it.days[0]
    assert day_fatigue(day) <= 9
    assert any("피로 예산" in a for a in it.assumptions)


# ── 균형과 빈 날 ────────────────────────────────────────────

def test_four_city_places_in_two_days_are_split_evenly(make_profile):
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4, 2)
    assert sorted(len(attractions(d)) for d in it.days) == [2, 2]


def test_no_day_is_left_empty_when_there_are_enough_places(make_profile):
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4, 3)
    assert all(attractions(d) for d in it.days)


def test_at_most_three_places_a_day_by_default(make_profile):
    it = plan(make_profile(age=65, walking_duration="1_2hour"), CITY6, 2)
    assert max(len(attractions(d)) for d in it.days) <= 3


# ── 불가능할 때는 안내 ──────────────────────────────────────

def test_too_many_places_for_a_weak_traveler_are_reported_not_squeezed_in(make_profile):
    profile = make_profile(age=78, walking_duration="under_15min")       # 예산 8
    it = plan(profile, CITY6, 2)
    assert it.unscheduled and all("피로 예산" in u.reason for u in it.unscheduled)
    placed = {p for d in it.days for p in attractions(d)}
    assert placed.isdisjoint({u.place_id for u in it.unscheduled})
    assert any("일정에 넣지 못했습니다" in a for a in it.assumptions)


# ── 하루 2끼, 한식, 식당 중복 ───────────────────────────────

def test_every_day_with_places_has_lunch_and_dinner(make_profile, restaurants):
    it = plan(make_profile(), CITY4 + ["dad-03"], 3, rest=restaurants)
    for d in it.days:
        if attractions(d):
            assert [s.meal for s in d.stops if s.type == "meal"] == ["lunch", "dinner"], d.day


def test_no_restaurant_is_used_twice(make_profile, restaurants):
    it = plan(make_profile(), CITY4 + ["dad-03", "dad-14"], 4, rest=restaurants)
    ids = [s.restaurant.place_id for d in it.days for s in d.stops if s.type == "meal" and s.restaurant]
    assert len(ids) == len(set(ids))


def test_korean_every_two_three_days_counts_over_the_whole_trip(make_profile, restaurants):
    it = plan(make_profile(korean_need="every_2_3_days"), CITY4 + ["dad-03", "dad-14"], 4, rest=restaurants)
    days = sum(any(s.restaurant and s.restaurant.is_korean for s in d.stops if s.type == "meal") for d in it.days)
    assert days >= math.ceil(len(it.days) / 2)


def test_daily_korean_gives_every_day_a_korean_meal(make_profile, restaurants):
    it = plan(make_profile(korean_need="daily"), CITY4, 2, rest=restaurants)
    for d in it.days:
        assert any(s.restaurant and s.restaurant.is_korean for s in d.stops if s.type == "meal"), d.day


# ── 고정과 대체 경로 ────────────────────────────────────────

def test_pinned_places_stay_on_their_day(make_profile):
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4, 2, state={"pins": {"dad-05": 2, "dad-06": 2}})
    day2 = {p for p in attractions(it.days[1])}
    assert {"dad-05", "dad-06"} <= day2


def test_a_pinned_group_over_the_limit_falls_back_to_the_old_assignment(make_profile):
    ids = CITY6
    pins = {p: 1 for p in ids}                       # 하루에 6곳을 고정: 새 구성이 다루지 않는 입력
    req = PlanRequest(travelers=[make_profile()], place_ids=ids, days=2, start_date=MONDAY, state=PlanState(pins=pins))
    ctx = _build_ctx(req, Restaurants())
    with pytest.raises(ComposeUnsupported):
        compose_days(ctx, ids, 2, select_modes)
    it = build_itinerary(req, Restaurants())          # 기존 방식으로 처리되어 일정은 나온다
    assert len(it.days) == 2
