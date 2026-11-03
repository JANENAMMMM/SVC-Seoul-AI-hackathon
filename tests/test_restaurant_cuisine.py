"""식당 수집 규칙 테스트. Google API를 호출하지 않는다."""

import httpx
import pytest

from src.restaurants import google_places
from src.restaurants.cuisine import classify
from src.restaurants.google_places import build_request_body, parse_place

FULL_PLACE = {
    "id": "place-1",
    "displayName": {"text": "마담 란", "languageCode": "ko"},
    "location": {"latitude": 16.07, "longitude": 108.22},
    "primaryType": "vietnamese_restaurant",
    "rating": 4.4,
    "userRatingCount": 2310,
    "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
    "regularOpeningHours": {
        "periods": [
            {"open": {"day": 1, "hour": 6, "minute": 30}, "close": {"day": 1, "hour": 21, "minute": 0}}
        ],
        "weekdayDescriptions": ["월요일: 오전 6:30~오후 9:00"],
    },
}


def test_build_request_body():
    body = build_request_body(16.0, 108.26, radius_m=800)
    assert body["includedTypes"] == ["restaurant"]
    assert body["maxResultCount"] == 20
    assert body["languageCode"] == "ko"
    assert body["locationRestriction"]["circle"]["radius"] == 800
    assert body["locationRestriction"]["circle"]["center"] == {"latitude": 16.0, "longitude": 108.26}
    # 카페·술집은 대표 타입 기준으로 제외, 세부 식당 타입은 막지 않음
    assert "cafe" in body["excludedPrimaryTypes"] and "bar" in body["excludedPrimaryTypes"]
    assert "includedPrimaryTypes" not in body


def test_build_request_body_rejects_over_20():
    with pytest.raises(ValueError):
        build_request_body(16.0, 108.26, max_results=21)


def test_field_mask_matches_step1_spec():
    expected = {
        "id", "displayName", "location",  # 다음 단계용
        "primaryType", "rating", "userRatingCount", "priceLevel", "regularOpeningHours",
    }
    assert set(google_places.FIELD_MASK.split(",")) == {f"places.{f}" for f in expected}


def test_parse_full_place():
    r = parse_place(FULL_PLACE)
    assert r.name == "마담 란"
    assert (r.lat, r.lng) == (16.07, 108.22)
    assert r.primary_type == "vietnamese_restaurant"
    assert r.rating == 4.4 and r.rating_count == 2310
    assert r.price_level == "PRICE_LEVEL_INEXPENSIVE"
    assert r.opening_periods[0].open_time == "06:30"
    assert r.opening_periods[0].close_time == "21:00"


def test_parse_minimal_place():
    r = parse_place({"id": "place-2", "displayName": {"text": "Bánh mì"}, "location": {}})
    assert r.rating is None
    assert r.price_level is None
    assert r.opening_periods == []


def test_parse_24h_place_has_no_close():
    raw = {"id": "p", "regularOpeningHours": {"periods": [{"open": {"day": 0, "hour": 0, "minute": 0}}]}}
    period = parse_place(raw).opening_periods[0]
    assert period.close_day is None and period.close_time is None


def test_search_uses_field_mask_and_parses(monkeypatch):
    monkeypatch.setattr(google_places, "_api_key", lambda: "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Goog-FieldMask"] == google_places.FIELD_MASK
        assert request.headers["X-Goog-Api-Key"] == "test-key"
        return httpx.Response(200, json={"places": [FULL_PLACE]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    results = google_places.search_nearby_restaurants(16.0, 108.26, client=client)
    assert [r.place_id for r in results] == ["place-1"]


@pytest.mark.parametrize(
    "primary, types, expected",
    [
        ("korean_restaurant", ["restaurant"], "korean"),
        ("vietnamese_restaurant", [], "southeast_asian"),
        ("restaurant", ["seafood_restaurant", "restaurant"], "seafood"),
        (None, ["sushi_restaurant"], "japanese"),
        ("restaurant", ["restaurant", "food"], "other"),
    ],
)
def test_classify_tag(primary, types, expected):
    assert classify(primary, types).tag == expected


def test_classify_flags():
    korean = classify("korean_barbecue_restaurant", [])
    assert korean.is_korean and not korean.has_seafood_type

    sushi = classify("sushi_restaurant", [])
    assert sushi.has_seafood_type  # 해산물을 피하면 제외 대상


def test_classify_local_depends_on_country():
    assert classify("vietnamese_restaurant", [], country="VN").is_local is True
    assert classify("vietnamese_restaurant", [], country="th").is_local is False
    assert classify("vietnamese_restaurant", []).is_local is None
