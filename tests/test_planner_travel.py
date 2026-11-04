import datetime

from src.planner.engine import build_itinerary
from src.planner.geo import travel_leg
from src.planner.schema import PlanRequest
from src.planner.sources import Restaurants, load_places, load_settings

IDS = [f"dad-{i:02d}" for i in (1, 2, 3, 5, 6, 7, 8, 14)]
TRAVEL = load_settings()["travel"]
DINNER_EARLIEST = load_settings()["meal"]["dinner_earliest"]  # "HH:MM"
_DE_MIN = int(DINNER_EARLIEST[:2]) * 60 + int(DINNER_EARLIEST[3:])


def plan(profile, restaurants=None, ids=IDS, days=4):
    req = PlanRequest(travelers=[profile], place_ids=ids, days=days, start_date=datetime.date(2026, 12, 7))
    return build_itinerary(req, restaurants if restaurants is not None else Restaurants())


def test_short_trip_walks_and_long_trip_takes_taxi():
    a = (16.0680836, 108.224069)
    near = (16.0700, 108.2245)
    far = (16.0037, 108.2632)
    assert travel_leg(a, near, 0.95, TRAVEL, 40)[1] == "walk"
    assert travel_leg(a, far, 0.95, TRAVEL, 40)[1] == "taxi"


def test_slower_walkers_and_tight_limits_take_taxi_sooner():
    a, b = (16.0680836, 108.224069), (16.0725, 108.2245)
    assert travel_leg(a, b, 1.2, TRAVEL, 40)[1] == "walk"
    assert travel_leg(a, b, 0.6, TRAVEL, 40)[1] == "taxi"
    assert travel_leg(a, b, 1.2, TRAVEL, 5)[1] == "taxi"


def test_same_place_needs_no_move():
    a = (16.0680836, 108.224069)
    assert travel_leg(a, a, 0.95, TRAVEL, 40) == (0, "walk")


def test_every_move_is_walk_or_taxi(make_profile, restaurants):
    it = plan(make_profile(), restaurants)
    moves = [s for d in it.days for s in d.stops if s.type == "move"]
    assert moves and all(m.transport in ("walk", "taxi") and m.minutes > 0 for m in moves)
    assert any(m.transport == "taxi" for m in moves)


def test_walking_moves_count_toward_walking_totals(make_profile):
    it = plan(make_profile(walking_duration="over_2hour", age=55, gender="male"))
    for d in it.days:
        attraction = sum(s.walk_min or 0 for s in d.stops if s.type == "attraction")
        walking = sum(s.minutes for s in d.stops if s.type == "move" and s.transport == "walk")
        assert d.total_walk_min == attraction + walking, d.day
        assert d.max_continuous_walk_min <= 90


def test_restaurant_trip_is_added_around_the_meal(make_profile, restaurants):
    it = plan(make_profile(), restaurants)
    checked = 0
    for d in it.days:
        for i, s in enumerate(d.stops):
            if s.type != "meal" or not s.restaurant or s.fixed or not s.restaurant.travel_min:
                continue
            go, back = d.stops[i - 1], d.stops[i + 1]
            assert go.type == "move" and go.note == f"→ {s.restaurant.name}" and go.end == s.start
            assert back.type == "move" and back.start == s.end
            assert go.minutes == back.minutes == s.restaurant.travel_min <= 10
            assert go.transport == back.transport == s.restaurant.transport
            checked += 1
    assert checked >= 3


def test_pinned_in_site_buffet_has_no_travel(make_profile, restaurants):
    it = plan(make_profile(), restaurants)
    lunch = next(s for d in it.days for s in d.stops if s.type == "meal" and s.fixed)
    assert lunch.restaurant.travel_min in (None, 0)


def test_meal_stops_stay_after_the_earliest_meal_times(make_profile, restaurants):
    it = plan(make_profile(), restaurants)
    for d in it.days:
        for s in d.stops:
            if s.type == "meal":
                h, m = map(int, s.start.split(":"))
                assert h * 60 + m >= (720 if s.meal == "lunch" else _DE_MIN)


def test_places_load_for_distance_sanity():
    places = load_places()
    leg = travel_leg(places["dad-07"].coord, places["dad-03"].coord, 0.95, TRAVEL, 40)
    assert leg[1] == "taxi" and 40 <= leg[0] <= 80


def test_every_non_empty_day_starts_and_ends_at_the_base_point(make_profile, restaurants):
    it = plan(make_profile(), restaurants)
    for d in it.days:
        assert d.stops[0].type == "base" and d.stops[0].start == "09:00" and "출발" in d.stops[0].note
        assert d.stops[-1].type == "base" and "복귀" in d.stops[-1].note
        assert sum(s.type == "base" for s in d.stops) == 2


def test_base_label_uses_default_name_but_not_for_custom_start_point(make_profile):
    default = plan(make_profile(), ids=["dad-05"], days=1)
    assert "다낭 시내 기준점" in default.days[0].stops[0].note
    custom = build_itinerary(PlanRequest(travelers=[make_profile()], place_ids=["dad-05"], days=1,
                                         start_point={"lat": 16.05, "lng": 108.22}), Restaurants())
    assert custom.days[0].stops[0].note == "출발: 출발지"


def test_empty_days_have_no_base_stops(make_profile):
    it = plan(make_profile(), ids=["dad-05"], days=3)
    assert [len(d.stops) for d in it.days][1:] == [0, 0]


def test_banahills_day_always_gets_a_dinner_in_the_city(make_profile, restaurants):
    for korean in ("none", "occasional"):
        it = plan(make_profile(korean_need=korean), restaurants, ids=["dad-01", "dad-05", "dad-07"], days=3)
        day = next(d for d in it.days if any(s.place_id == "dad-01" for s in d.stops))
        meals = [s for s in day.stops if s.type == "meal"]
        assert [m.meal for m in meals] == ["lunch", "dinner"], korean
        assert meals[0].fixed and not meals[1].fixed and meals[1].restaurant is not None
        i = day.stops.index(meals[1])
        assert any(s.type == "move" and s.note == "→ 다낭 시내" for s in day.stops[:i])
        assert day.stops[-1].type == "base" and meals[1].start >= DINNER_EARLIEST


def test_every_far_from_city_day_gets_a_dinner_even_when_it_ends_early(make_profile, restaurants):
    from src.planner.schema import DayWindow
    far = {"dad-01": "바나힐", "dad-03": "호이안", "dad-11": "누이탄타이", "dad-12": "미선", "dad-15": "껌탄"}
    for pid, name in far.items():
        req = PlanRequest(travelers=[make_profile()], place_ids=[pid, "dad-07"], days=2,
                          start_date=datetime.date(2026, 12, 7), day_window=DayWindow(start="07:00", end="21:00"))
        it = build_itinerary(req, restaurants)
        day = next(d for d in it.days if any(s.place_id == pid for s in d.stops))
        assert "dinner" in [s.meal for s in day.stops if s.type == "meal"], name


def test_near_city_day_that_ends_early_still_gets_two_meals(make_profile, restaurants):  # 하루 항상 2끼
    from src.planner.schema import DayWindow
    req = PlanRequest(travelers=[make_profile()], place_ids=["dad-07"], days=1,
                      start_date=datetime.date(2026, 12, 7), day_window=DayWindow(start="08:00", end="21:00"))
    day = build_itinerary(req, restaurants).days[0]
    assert [s.meal for s in day.stops if s.type == "meal"] == ["lunch", "dinner"]


def test_low_stamina_note_names_the_short_course_instead_of_generic_wording(make_profile):
    it = plan(make_profile(age=78, walking_duration="under_15min"), ids=["dad-02", "dad-07"], days=2)
    notes = [a for a in it.assumptions if "보행 한도가 짧아" in a]
    assert any("'엘리베이터·사원 일부' 코스로 잡았습니다" in a for a in notes), it.assumptions
    assert not any("이동 보조" in a or "짧은 관람" in a for a in it.assumptions)
