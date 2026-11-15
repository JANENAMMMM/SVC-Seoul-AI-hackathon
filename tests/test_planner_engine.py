import datetime

import pytest

from src.planner.engine import build_itinerary
from src.planner.hours import earliest_start, hhmm_to_min, intervals_for
from src.planner.schema import PlanRequest
from src.planner.sources import Restaurants, load_places, load_settings

DINNER_EARLIEST = hhmm_to_min(load_settings()["meal"]["dinner_earliest"])
MONDAY = datetime.date(2026, 12, 7)
SUNDAY = datetime.date(2026, 12, 6)
EIGHT = [f"dad-{i:02d}" for i in (1, 2, 3, 5, 6, 7, 8, 14)]


def plan(profile, place_ids=EIGHT, days=4, start=MONDAY, restaurants=None, state=None):
    body = {"travelers": [profile], "place_ids": place_ids, "days": days, "start_date": start}
    if state:
        body["state"] = state
    return build_itinerary(PlanRequest(**body), restaurants if restaurants is not None else Restaurants())


def attraction_stops(day):
    return [s for s in day.stops if s.type == "attraction"]


def meals(it):
    return [(d.day, s) for d in it.days for s in d.stops if s.type == "meal"]


def test_all_selected_places_are_scheduled(make_profile):
    it = plan(make_profile())
    scheduled = {s.place_id for d in it.days for s in attraction_stops(d)}
    assert scheduled == set(EIGHT)
    assert not it.unscheduled
    assert all(d.stops for d in it.days)


def test_attractions_stay_inside_opening_hours(make_profile):
    places = load_places()
    it = plan(make_profile())
    for d in it.days:
        wd = (MONDAY.weekday() + d.day - 1) % 7
        for s in attraction_stops(d):
            start, end = hhmm_to_min(s.start), hhmm_to_min(s.end)
            intervals = intervals_for(places[s.place_id].hours, wd)
            assert earliest_start(intervals, start, end - start) == start, (d.day, s.name, s.start, s.end)


def test_clusters_are_not_mixed_within_a_day(make_profile):
    places = load_places()
    it = plan(make_profile())
    for d in it.days:
        assert len({places[s.place_id].cluster for s in attraction_stops(d)}) <= 1


def test_banahills_is_solo_day_with_pinned_buffet_lunch(make_profile, restaurants):
    it = plan(make_profile(), restaurants=restaurants)
    day = next(d for d in it.days if any(s.place_id == "dad-01" for s in attraction_stops(d)))
    assert {s.place_id for s in attraction_stops(day)} == {"dad-01"}
    lunch = next(s for s in day.stops if s.type == "meal" and s.meal == "lunch")
    assert lunch.fixed and "뷔페" in lunch.restaurant.name
    assert 630 <= hhmm_to_min(lunch.start) and hhmm_to_min(lunch.end) <= 900


def test_meal_time_windows(make_profile, restaurants):
    it = plan(make_profile(), restaurants=restaurants)
    for _, s in meals(it):
        start = hhmm_to_min(s.start)
        assert start >= (720 if s.meal == "lunch" else DINNER_EARLIEST), (s.meal, s.start)


def test_restaurants_are_unique_and_valid(make_profile, restaurants):
    it = plan(make_profile(), restaurants=restaurants)
    picks = [s.restaurant for _, s in meals(it) if s.restaurant]
    ids = [p.place_id for p in picks]
    assert ids and len(ids) == len(set(ids))
    assert not any(i.endswith(("-hotel", "-new")) for i in ids)
    assert len(picks) == len(meals(it))


def test_seafood_avoidance_filters_seafood_only_when_requested(make_profile, restaurants):
    with_seafood = plan(make_profile(), restaurants=restaurants)
    avoided = plan(make_profile(avoid_ingredients=["seafood"]), restaurants=restaurants)
    assert any(s.restaurant and s.restaurant.place_id.endswith("-sea") for _, s in meals(with_seafood))
    assert not any(s.restaurant and s.restaurant.place_id.endswith("-sea") for _, s in meals(avoided))


def test_daily_korean_need_gets_real_korean_restaurant_each_day(make_profile, restaurants):
    it = plan(make_profile(korean_need="daily"), restaurants=restaurants)
    for d in it.days:
        day_meals = [s for s in d.stops if s.type == "meal" and s.restaurant]
        if not day_meals:
            continue
        assert any(s.restaurant.place_id.endswith("-kor") for s in day_meals), d.day


def test_korean_slot_uses_is_korean_flag_from_data(make_profile, restaurants):
    from src.planner.meals import choose_restaurant
    from src.planner.profile_merge import merge_profiles
    from src.planner.schema import PlanState
    from src.planner.sources import load_settings

    settings = load_settings()
    profile = merge_profiles([make_profile(korean_need="daily")], PlanState(), settings)
    anchor = load_places()["dad-07"].coord
    pick = choose_restaurant(restaurants, anchor, 1080, 1140, None, profile, settings, set(), need_korean=True)
    assert pick.is_korean and pick.place_id.endswith("-kor")


def test_every_two_three_days_needs_korean_on_at_least_half_the_days(make_profile, restaurants):
    # 한식은 여행 전체 조건이다: 2~3일에 한 번 = ceil(일수/2)일 이상. 어느 날이어도 된다(한식당이 있는 날로 옮길 수 있음).
    it = plan(make_profile(korean_need="every_2_3_days"), restaurants=restaurants)
    has_korean = {d.day: any(s.type == "meal" and s.restaurant and s.restaurant.place_id.endswith("-kor")
                             for s in d.stops) for d in it.days}
    assert sum(has_korean.values()) >= (len(it.days) + 1) // 2, has_korean


def test_continuous_walk_limit_follows_profile(make_profile):
    tight = plan(make_profile(walking_duration="under_15min"))
    relaxed = plan(make_profile(walking_duration="over_2hour"))
    assert all(d.max_continuous_walk_min <= 12 for d in tight.days)
    assert all(d.max_continuous_walk_min <= 90 for d in relaxed.days)
    rests = lambda it: sum(s.type == "rest" for d in it.days for s in d.stops)
    assert rests(tight) >= rests(relaxed)


def test_low_stamina_uses_short_mode_but_healthy_does_not(make_profile):
    tight = plan(make_profile(), place_ids=["dad-02"], days=1)
    healthy = plan(make_profile(age=55, gender="male", walking_duration="over_2hour"), place_ids=["dad-02"], days=1)
    assert attraction_stops(tight.days[0])[0].mode == "short"
    assert attraction_stops(healthy.days[0])[0].mode == "standard"


def test_sunday_closure_moves_cathedral_to_another_day(make_profile):
    it = plan(make_profile(), place_ids=["dad-08", "dad-06"], days=2, start=SUNDAY)
    day_of = {s.place_id: d.day for d in it.days for s in attraction_stops(d)}
    assert day_of["dad-08"] == 2
    assert not it.unscheduled


def test_closed_place_on_single_day_is_reported(make_profile):
    it = plan(make_profile(), place_ids=["dad-08"], days=1, start=SUNDAY)
    assert [u.place_id for u in it.unscheduled] == ["dad-08"]
    assert "영업시간" in it.unscheduled[0].reason


def test_evening_market_opens_after_17_and_every_requested_day_is_used(make_profile):
    # 일정 일수만큼 모든 날을 쓴다. 이전에는 야시장을 구시가지와 같은 날로 묶었지만, 이제는 장소 2곳·2일이면
    # 하루에 한 곳씩 간다(야시장만 있는 날은 개장 시각 전까지 빈 시간이 생긴다).
    it = plan(make_profile(), place_ids=["dad-03", "dad-14"], days=2)
    day_of = {s.place_id: d.day for d in it.days for s in attraction_stops(d)}
    assert set(day_of.values()) == {1, 2}
    market = next(s for d in it.days for s in attraction_stops(d) if s.place_id == "dad-14")
    assert hhmm_to_min(market.start) >= 17 * 60


def test_pins_are_respected(make_profile):
    it = plan(make_profile(), state={"pins": {"dad-07": 3}})
    day_of = {s.place_id: d.day for d in it.days for s in attraction_stops(d)}
    assert day_of["dad-07"] == 3


def test_difficulty_and_package_are_reported(make_profile):
    it = plan(make_profile())
    assert all(d.difficulty for d in it.days)
    assert it.package.peak == max(d.difficulty for d in it.days)


def test_assumptions_flag_defaults_and_manual_hours(make_profile):
    text = "\n".join(plan(make_profile()).assumptions)
    assert "가정" in text and "호이안 야시장" in text and "식당 데이터" in text


def test_unknown_place_is_rejected(make_profile):
    with pytest.raises(ValueError):
        plan(make_profile(), place_ids=["dad-99"], days=1)


def test_state_pins_cover_every_scheduled_place(make_profile):
    it = plan(make_profile())
    assert set(it.state.pins) == set(EIGHT)
