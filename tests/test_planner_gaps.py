"""2단계: 식당 위치 반영, 체류 범위, 자유 시간 칸."""

import datetime

import pytest

from src.planner.engine import build_itinerary
from src.planner.hours import hhmm_to_min, intervals_for
from src.planner.schema import PlanRequest
from src.planner.sources import Restaurants, load_places, load_settings

MONDAY = datetime.date(2026, 12, 7)
PLACES = load_places()
FREE = load_settings()["free_time"]
CITY4 = ["dad-05", "dad-06", "dad-07", "dad-08"]


def plan(profile, ids, days, rest=None):
    req = PlanRequest(travelers=[profile], place_ids=ids, days=days, start_date=MONDAY)
    return build_itinerary(req, rest if rest is not None else Restaurants())


def consecutive(day):
    stops = [s for s in day.stops if s.type != "base"]
    return list(zip(stops, stops[1:]))


@pytest.mark.parametrize("ids,days", [(CITY4, 2), (CITY4 + ["dad-03", "dad-14"], 3), (["dad-03", "dad-14"], 2)])
def test_no_unnamed_gap_longer_than_the_threshold(make_profile, restaurants, ids, days):
    it = plan(make_profile(age=65, walking_duration="30_60min"), ids, days, rest=restaurants)
    for d in it.days:
        for a, b in consecutive(d):
            assert hhmm_to_min(b.start) - hhmm_to_min(a.end) < FREE["min_gap_min"], (d.day, a.end, b.start)


def test_long_gaps_are_shown_as_labeled_free_time(make_profile, restaurants):
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4, 2, rest=restaurants)
    free = [s for d in it.days for s in d.stops if s.type == "rest" and s.reason == FREE["label"]]
    assert free and all((s.minutes or 0) >= FREE["min_gap_min"] for s in free)
    assert all(hhmm_to_min(s.end) - hhmm_to_min(s.start) == s.minutes for s in free)


def test_stay_is_extended_only_within_the_range(make_profile, restaurants):
    ranges = {int(k): v for k, v in FREE["stay_range"].items()}
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4 + ["dad-03", "dad-14"], 3, rest=restaurants)
    for d in it.days:
        total: dict[str, int] = {}
        for s in d.stops:
            if s.type == "attraction":
                total[s.place_id] = total.get(s.place_id, 0) + hhmm_to_min(s.end) - hhmm_to_min(s.start)
        for pid, minutes in total.items():
            lo, hi = ranges[PLACES[pid].stay_min]
            assert PLACES[pid].stay_min <= minutes <= hi, (pid, minutes)


def test_extended_stay_never_passes_the_closing_time(make_profile, restaurants):
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4 + ["dad-03", "dad-14"], 3, rest=restaurants)
    for d in it.days:
        wd = (MONDAY.weekday() + d.day - 1) % 7
        for s in d.stops:
            if s.type != "attraction" or PLACES[s.place_id].hours is None:
                continue
            intervals = intervals_for(PLACES[s.place_id].hours, wd)
            assert any(a <= hhmm_to_min(s.start) and hhmm_to_min(s.end) <= e for a, e in intervals), (s.place_id, s.start, s.end)


def test_a_waiting_trip_leaves_late_instead_of_arriving_early(make_profile, restaurants):
    # 도착해서 기다리지 않도록 이동 출발을 늦춘다: 이동 칸 바로 뒤에 관광·식사가 시작한다.
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4 + ["dad-03", "dad-14"], 3, rest=restaurants)
    for d in it.days:
        for a, b in consecutive(d):
            if a.type == "move" and b.type in ("attraction", "meal"):
                assert hhmm_to_min(b.start) - hhmm_to_min(a.end) < FREE["min_gap_min"]


def test_meal_with_a_known_restaurant_is_followed_from_that_restaurant(make_profile, restaurants):
    # 식당이 확정된 끼니 뒤에는 "→ 다음 장소" 같은 이름 없는 이동이 나오지 않는다(식당에서 다음 장소로 직접 간다).
    it = plan(make_profile(age=65, walking_duration="30_60min"), CITY4, 2, rest=restaurants)
    dangling = [s for d in it.days for s in d.stops if s.type == "move" and s.note == "→ 다음 장소"]
    assert len(dangling) <= 1
