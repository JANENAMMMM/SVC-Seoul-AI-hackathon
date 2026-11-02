"""2~6단계 테스트. 외부 API는 호출하지 않고 가짜 데이터·가짜 HTTP로 확인한다."""

import httpx

from src.restaurants import google_reviews
from src.restaurants.collect import Attraction, collect, review_info
from src.restaurants.google_places import OpeningPeriod, Restaurant
from src.restaurants.google_reviews import PlaceReviews, Review, parse_details
from src.restaurants.keywords import analyze
from src.restaurants.preferences import FoodPreference
from src.restaurants.ranking import (
    bayesian_rating,
    build_candidates,
    distance_m,
    is_open_at,
    open_for_meals,
    select_top,
)

EVERY_DAY_11_TO_22 = [
    OpeningPeriod(open_day=d, open_time="11:00", close_day=d, close_time="22:00") for d in range(7)
]


def make(place_id, primary_type="vietnamese_restaurant", rating=4.5, count=500, hours=None, name=None):
    return Restaurant(
        place_id=place_id,
        name=name or place_id,
        lat=16.07,
        lng=108.22,
        primary_type=primary_type,
        rating=rating,
        rating_count=count,
        opening_periods=EVERY_DAY_11_TO_22 if hours is None else hours,
    )


# ── 2단계: 영업시간 ──────────────────────────────────────────

def test_is_open_at_normal_hours():
    r = make("a")
    assert is_open_at(r, 1, "12:00")
    assert not is_open_at(r, 1, "10:00")
    assert not is_open_at(r, 1, "22:00")


def test_is_open_past_midnight():
    r = make("a", hours=[OpeningPeriod(open_day=5, open_time="18:00", close_day=6, close_time="02:00")])
    assert is_open_at(r, 5, "23:00")
    assert is_open_at(r, 6, "01:30")
    assert not is_open_at(r, 6, "03:00")


def test_is_open_week_wrap_saturday_to_sunday():
    r = make("a", hours=[OpeningPeriod(open_day=6, open_time="20:00", close_day=0, close_time="01:00")])
    assert is_open_at(r, 0, "00:30")


def test_24h_has_no_close():
    r = make("a", hours=[OpeningPeriod(open_day=0, open_time="00:00")])
    assert open_for_meals(r)


def test_closed_on_one_day_fails_meal_check():
    hours = [p for p in EVERY_DAY_11_TO_22 if p.open_day != 1]  # 월요일 휴무
    assert not open_for_meals(make("a", hours=hours))
    assert open_for_meals(make("a", hours=hours), days=frozenset({2, 3}))


def test_dinner_only_still_passes():
    hours = [OpeningPeriod(open_day=d, open_time="17:00", close_day=d, close_time="23:00") for d in range(7)]
    assert open_for_meals(make("a", hours=hours))


# ── 2~3단계: 거르기·점수·상위 5 ─────────────────────────────

def test_bayesian_keeps_few_reviews_from_jumping():
    prior = 4.2
    assert bayesian_rating(5.0, 3, prior) < bayesian_rating(4.6, 2000, prior)
    assert bayesian_rating(None, None, prior) == prior


def test_distance():
    assert distance_m(16.0, 108.0, 16.0, 108.0) == 0
    assert 1100 < distance_m(16.0, 108.0, 16.01, 108.0) < 1120  # 위도 0.01도 ≈ 1.11km


def test_filters_seafood_and_closed():
    pref = FoodPreference(avoid_ingredients=["seafood"])
    closed_lunch_dinner = [OpeningPeriod(open_day=d, open_time="06:00", close_day=d, close_time="10:00") for d in range(7)]
    cands = build_candidates(
        [make("sea", "seafood_restaurant"), make("early", hours=closed_lunch_dinner), make("ok")], pref
    )
    reasons = {c.restaurant.place_id: c.excluded_reason for c in cands}
    assert reasons["sea"] and "해산물" in reasons["sea"]
    assert reasons["early"] and "문을 닫" in reasons["early"]
    assert reasons["ok"] is None


def test_unknown_hours_kept_and_flagged():
    cands = build_candidates([make("x", hours=[])], FoodPreference())
    assert cands[0].excluded_reason is None and cands[0].hours_unknown


def test_duplicates_removed():
    cands = build_candidates([make("a"), make("a")], FoodPreference())
    assert len(cands) == 1


def test_local_food_familiar_lowers_local_score():
    rs = [make("vn", "vietnamese_restaurant"), make("cn", "chinese_restaurant")]
    familiar = {c.restaurant.place_id: c.score for c in build_candidates(rs, FoodPreference(local_food="familiar"), country="VN")}
    assert familiar["vn"] < familiar["cn"]
    adventurous = {c.restaurant.place_id: c.score for c in build_candidates(rs, FoodPreference(local_food="adventurous"), country="VN")}
    assert adventurous["vn"] > adventurous["cn"]


def test_top5_includes_korean_when_needed():
    rs = [make(f"vn{i}", rating=4.8 - i * 0.05) for i in range(6)] + [make("kr", "korean_restaurant", rating=4.0)]
    pref = FoodPreference(korean_need="daily")
    top = select_top(build_candidates(rs, pref), pref)
    assert len(top) == 5
    assert top[-1].restaurant.place_id == "kr"

    no_need = FoodPreference(korean_need="none")
    top = select_top(build_candidates(rs, no_need), no_need)
    assert all(not c.cuisine.is_korean for c in top)


# ── 4단계: Google 리뷰 ───────────────────────────────────────

DETAILS = {
    "reviews": [
        {
            "rating": 5,
            "text": {"text": "부모님도 잘 드셨어요. 새우가 많아요", "languageCode": "ko"},
            "originalText": {"text": "부모님도 잘 드셨어요. 새우가 많아요", "languageCode": "ko"},
            "authorAttribution": {"displayName": "김", "uri": "https://maps.google.com/u1"},
            "publishTime": "2026-10-01T00:00:00Z",
        },
        {
            "rating": 4,
            "text": {"text": "맛있어요 (번역됨)", "languageCode": "ko"},
            "originalText": {"text": "Delicious food", "languageCode": "en"},
            "authorAttribution": {"displayName": "John"},
        },
    ],
    "reviewSummary": {
        "text": {"text": "현지 음식이 무난하고 직원이 친절하다는 평이 많아요.", "languageCode": "ko"},
        "disclosureText": {"text": "Gemini로 요약됨", "languageCode": "ko"},
        "reviewsUri": "https://maps.google.com/reviews",
    },
}


def test_parse_details_and_korean_filter():
    place = parse_details(DETAILS)
    assert len(place.reviews) == 2
    assert [r.author for r in place.korean_reviews] == ["김"]  # 원문이 한국어인 리뷰만
    assert place.reviews[1].original_text == "Delicious food"
    assert place.summary.startswith("현지 음식이")
    assert place.summary_disclosure == "Gemini로 요약됨"


def test_parse_details_empty():
    place = parse_details({})
    assert place.reviews == [] and place.summary is None


def test_korean_language_variants():
    assert Review(original_language="ko-KR").is_korean
    assert not Review(original_language="vi").is_korean
    assert not Review(original_language=None).is_korean


def test_fetch_reviews_request(monkeypatch):
    monkeypatch.setattr(google_reviews, "_api_key", lambda: "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/places/place-1"
        assert request.url.params["languageCode"] == "ko"
        assert request.headers["X-Goog-FieldMask"] == "reviews,reviewSummary"
        return httpx.Response(200, json=DETAILS)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert len(google_reviews.fetch_reviews("place-1", client=client).reviews) == 2


def test_review_info_uses_korean_reviews_and_summary():
    pref = FoodPreference(avoid_ingredients=["seafood"])
    info = review_info(parse_details(DETAILS), pref)
    assert info.returned_count == 2 and len(info.korean_reviews) == 1
    assert info.signals.text_count == 2  # 한국어 리뷰 1 + 요약 1 (영어 원문 리뷰는 제외)
    assert "parents" in info.signals.tags and "familiar_taste" in info.signals.tags
    assert any("해산물" in w for w in info.signals.warnings)


# ── 5단계: 키워드 ────────────────────────────────────────────

def test_keywords_warn_on_avoided_ingredient():
    texts = ["새우 요리가 맛있어요", "땅콩 빼달라고 했어요", "부모님도 잘 드셨어요"]
    pref = FoodPreference(avoid_ingredients=["seafood", "nuts"], local_food="familiar")
    signals = analyze(texts, pref)
    assert signals.tags["seafood"].count == 1
    assert signals.tags["parents"].count == 1
    assert any("해산물" in w for w in signals.warnings)
    assert any("견과류" in w and "요청 가능" in w for w in signals.warnings)


def test_keywords_other_and_street():
    texts = ["고수가 많이 들어가요", "노점 분위기 플라스틱 의자"]
    pref = FoodPreference(avoid_other=["고수"], venues=["restaurant"])
    warnings = analyze(texts, pref).warnings
    assert any("고수" in w for w in warnings)
    assert any("노점" in w for w in warnings)


def test_spicy_does_not_match_google_map():
    assert "spicy" not in analyze(["구글맵 보고 찾아감"], FoodPreference()).tags


# ── 1~6단계 전체 (가짜 API + 캐시) ───────────────────────────

def test_collect_end_to_end_with_cache(tmp_path):
    calls = {"google": [], "reviews": []}

    def fake_google(lat, lng, radius_m, included_types):
        calls["google"].append(included_types)
        if included_types == ("korean_restaurant",):
            return [make("kr", "korean_restaurant", rating=4.1, name="서울식당")]
        return [make(f"vn{i}", rating=4.7 - i * 0.05, name=f"식당{i}") for i in range(7)]

    def fake_reviews(place_id):
        calls["reviews"].append(place_id)
        return PlaceReviews(
            summary="부모님 모시고 가기 무난한 곳",
            reviews=[Review(original_text="부모님이 좋아하셨어요", original_language="ko")],
        )

    attractions = [Attraction(id="han", name="한 시장", lat=16.0684, lng=108.2241)]
    pref = FoodPreference(korean_need="daily", local_food="familiar")
    run = lambda: collect(  # noqa: E731
        attractions, pref, city="다낭", country="VN", cache_dir=tmp_path,
        google_search=fake_google, review_fetch=fake_reviews,
    )

    result = run()
    restaurants = result.attractions[0].restaurants
    assert len(restaurants) == 5
    assert restaurants[-1].name == "서울식당"  # 한식이 없어서 한식당 1회 추가 검색 후 포함
    assert calls["google"] == [("restaurant",), ("korean_restaurant",)]
    assert len(calls["reviews"]) == 5
    assert restaurants[0].reviews.signals.tags["parents"].count == 2  # 리뷰 1 + 요약 1
    assert restaurants[0].distance_m is not None

    run()  # 두 번째 실행은 캐시만 사용
    assert len(calls["google"]) == 2 and len(calls["reviews"]) == 5
