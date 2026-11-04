"""대표 타입 허용 목록·쿠킹 클래스 제외 규칙 테스트. Google API는 호출하지 않는다."""

import pytest

from src.restaurants.google_places import OpeningPeriod, Restaurant
from src.restaurants.ranking import build_candidates, is_food_place

HOURS = [OpeningPeriod(open_day=d, open_time="10:00", close_day=d, close_time="22:00") for d in range(7)]


def make(pid, primary_type="restaurant", rating=4.5):
    return Restaurant(
        place_id=pid, name=pid, lat=16.07, lng=108.22, primary_type=primary_type,
        rating=rating, rating_count=500, opening_periods=HOURS,
    )


# ── 대표 타입 허용 목록 ──────────────────────────────────────

@pytest.mark.parametrize(
    "primary, ok",
    [
        ("restaurant", True), ("vietnamese_restaurant", True), ("buffet_restaurant", True),
        ("bistro", True), ("snack_bar", True), (None, True),
        ("resort_hotel", False), ("hotel", False), ("grocery_store", False),
    ],
)
def test_is_food_place(primary, ok):
    assert is_food_place(primary) is ok


def test_new_allowed_types():
    for t in ["sandwich_shop", "kebab_shop", "hot_dog_stand", "salad_shop", "deli", "gastropub", "bar_and_grill"]:
        assert is_food_place(t), t
    for t in ["cafe", "bakery", "pub", "bar", "cafeteria", "meal_takeaway"]:
        assert not is_food_place(t), t


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Tuong cooking class hoi an", True),
        ("Red Dragon Restaurant and Cooking Class", True),
        ("Hoi An Cooking School", True),
        ("호이안 쿠킹클래스", True),
        ("Lớp học nấu ăn Hội An", True),
        ("피자 4P's 다낭 인도차이나점", False),
        ("Cooking Mama Restaurant", False),  # 이름에 'cooking'만 있고 클래스는 아님
        ("Son Hoian", False),
    ],
)
def test_cooking_class_by_name(name, expected):
    from src.restaurants.ranking import is_cooking_class

    assert is_cooking_class(name) is expected


def test_cooking_class_excluded_by_name_not_reviews():
    """대표 타입이 restaurant여도 이름에 쿠킹 클래스가 있으면 제외한다."""
    cands = build_candidates(
        [make("c1", "korean_restaurant"), make("ok1", "pizza_restaurant")]
    )
    cands[0].restaurant.name = "Tuong cooking class hoi an"
    cands = build_candidates([cands[0].restaurant, cands[1].restaurant])
    reasons = {c.restaurant.place_id: c.excluded_reason for c in cands}
    assert "쿠킹 클래스" in reasons["c1"] and reasons["ok1"] is None


def test_hotel_excluded_with_reason():
    cands = build_candidates([make("h", "resort_hotel"), make("r")])
    reasons = {c.restaurant.place_id: c.excluded_reason for c in cands}
    assert "음식점이 아님" in reasons["h"] and reasons["r"] is None
