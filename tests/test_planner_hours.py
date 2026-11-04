import json
from pathlib import Path

from src.planner.hours import (earliest_start, has_weekday_closure, intervals_for, parse_google_hours,
                               parse_korean_hours)
from src.planner.sources import load_places

ROOT = Path(__file__).resolve().parents[1]


def _attraction(pid):
    data = json.loads((ROOT / "data" / "scoring" / "attractions.json").read_text(encoding="utf-8"))
    return next(a for a in data if a["id"] == pid)


def test_cathedral_has_midday_break_and_sunday_closure():
    hours = parse_google_hours(_attraction("dad-08")["google"]["hours"])
    assert hours[0] == [(480, 690), (810, 990)]
    assert hours[6] == []
    assert has_weekday_closure(hours)


def test_open_all_day_and_status_snapshot():
    assert parse_google_hours(_attraction("dad-06")["google"]["hours"])[3] == [(0, 1440)]
    assert parse_google_hours(_attraction("dad-14")["google"]["hours"]) is None


def test_korean_restaurant_hours_variants():
    assert parse_korean_hours(["월요일: 오전 10:30 ~ 오후 3:00"]) == {0: [(630, 900)]}
    assert parse_korean_hours(["월요일: 오후 12:00~10:00"]) == {0: [(720, 1320)]}
    assert parse_korean_hours(["월요일: 오전 9:00 ~ 오후 4:00, 오후 6:30~9:00"]) == {0: [(540, 960), (1110, 1260)]}
    assert parse_korean_hours(["월요일: 오후 4:00 ~ 오전 2:00"]) == {0: [(960, 1560)]}
    assert parse_korean_hours(["월요일: 24시간 영업"]) == {0: [(0, 1440)]}
    assert parse_korean_hours([]) is None


def test_earliest_start_waits_or_fails():
    assert earliest_start([(1020, 1320)], 600, 120) == 1020
    assert earliest_start([(480, 690), (810, 990)], 700, 60) == 810
    assert earliest_start([(480, 690)], 700, 60) is None
    assert earliest_start(None, 700, 60) == 700


def test_unknown_weekday_uses_most_common_pattern():
    hours = {0: [(480, 1020)], 1: [(480, 1020)], 6: []}
    assert intervals_for(hours, None) == [(480, 1020)]
    assert intervals_for(hours, 6) == []


def test_all_places_load_with_hours_source():
    places = load_places()
    assert len(places) == 15
    assert places["dad-14"].hours_source == "manual" and places["dad-14"].evening
    assert places["dad-08"].hours_source == "google" and not places["dad-08"].evening
    assert places["dad-10"].evening
    assert places["dad-01"].cluster == "banahills" and places["dad-01"].solo
