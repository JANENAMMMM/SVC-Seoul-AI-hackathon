"""2~6단계 테스트. 외부 API는 호출하지 않고 가짜 데이터·가짜 HTTP로 확인한다."""

import httpx

from src.restaurants import google_reviews
from src.restaurants.collect import Attraction, collect, review_info
from src.restaurants.google_places import OpeningPeriod, Restaurant
from src.restaurants.google_reviews import PlaceReviews, Review, parse_details
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


def test_filters_closed_but_keeps_seafood():
    closed_lunch_dinner = [OpeningPeriod(open_day=d, open_time="06:00", close_day=d, close_time="10:00") for d in range(7)]
    cands = build_candidates(
        [make("sea", "seafood_restaurant"), make("early", hours=closed_lunch_dinner), make("ok")]
    )
    reasons = {c.restaurant.place_id: c.excluded_reason for c in cands}
    assert reasons["sea"] is None  # 해산물은 프로필에 따라 일정 엔진이 거른다
    assert reasons["early"] and "문을 닫" in reasons["early"]
    assert reasons["ok"] is None


def test_unknown_hours_kept_and_flagged():
    cands = build_candidates([make("x", hours=[])])
    assert cands[0].excluded_reason is None and cands[0].hours_unknown


def test_duplicates_removed():
    cands = build_candidates([make("a"), make("a")])
    assert len(cands) == 1


def test_score_has_no_local_food_adjustment():
    # 같은 평점이면 현지 음식이어도 점수가 같다 (선호 보정은 일정 엔진에서)
    rs = [make("vn", "vietnamese_restaurant"), make("cn", "chinese_restaurant")]
    scores = {c.restaurant.place_id: c.score for c in build_candidates(rs, country="VN")}
    assert scores["vn"] == scores["cn"]


def test_top5_always_includes_korean():
    rs = [make(f"vn{i}", rating=4.8 - i * 0.03) for i in range(7)] + [make("kr", "korean_restaurant", rating=4.0)]
    top = select_top(build_candidates(rs))
    assert len(top) == 5
    assert top[-1].restaurant.place_id == "kr"


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


def test_review_info_keeps_korean_originals_unmodified():
    info = review_info(parse_details(DETAILS))
    assert info.returned_count == 2 and len(info.korean_reviews) == 1  # 영어 원문 리뷰는 빠짐
    assert info.korean_reviews[0].original_text == "부모님도 잘 드셨어요. 새우가 많아요"  # 가공 없음
    assert info.korean_reviews[0].author == "김"  # 작성자 표시용
    assert info.summary.startswith("현지 음식이")
    assert not hasattr(info, "signals")  # 태그·경고 없음


def test_fetch_place_for_display(monkeypatch):
    monkeypatch.setattr(google_reviews, "_api_key", lambda: "test-key")
    masks = []

    def handler(request: httpx.Request) -> httpx.Response:
        masks.append(request.headers["X-Goog-FieldMask"])
        body = {
            "displayName": {"text": "마담 란"},
            "location": {"latitude": 16.07, "longitude": 108.22},
            "rating": 4.4,
            "googleMapsUri": "https://maps.google.com/?cid=1",
            **DETAILS,
        }
        return httpx.Response(200, json=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    plain = google_reviews.fetch_place_for_display("place-1", client=client)
    assert plain.restaurant.place_id == "place-1" and plain.restaurant.name == "마담 란"
    assert plain.maps_url == "https://maps.google.com/?cid=1"
    assert plain.reviews is None and "reviews" not in masks[0]  # 리뷰 없이 = Enterprise 등급

    full = google_reviews.fetch_place_for_display("place-1", with_reviews=True, client=client)
    assert "reviews" in masks[1] and len(full.reviews.korean_reviews) == 1


# ── 1~6단계 전체 (가짜 API, 저장 없음) ───────────────────────

def test_collect_end_to_end_without_storage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # 혹시 파일을 쓰면 여기에 남아 테스트로 잡힘
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
    run = lambda atts: collect(  # noqa: E731
        atts, city="다낭", country="VN", tags=False,  # 태그(Claude)는 tests/test_restaurant_tags.py에서
        google_search=fake_google, review_fetch=fake_reviews,
    )

    result = run(attractions)
    restaurants = result.attractions[0].restaurants
    assert len(restaurants) == 5
    assert restaurants[-1].name == "서울식당"  # 한식이 없어서 한식당 1회 추가 검색 후 포함
    assert calls["google"] == [("restaurant",), ("korean_restaurant",)]
    assert len(calls["reviews"]) == 5
    assert restaurants[0].reviews.korean_reviews[0].original_text == "부모님이 좋아하셨어요"
    assert restaurants[0].distance_m is not None

    run(attractions)  # 캐시가 없으므로 다시 실행하면 다시 호출
    assert len(calls["google"]) == 4 and len(calls["reviews"]) == 10

    # 한 실행 안에서 같은 식당이 두 관광지에 나오면 리뷰는 1회만 조회
    calls["reviews"].clear()
    twin = [attractions[0], Attraction(id="bridge", name="용다리", lat=16.0612, lng=108.2272)]
    run(twin)
    assert len(calls["reviews"]) == 5

    assert list(tmp_path.iterdir()) == []  # 아무 파일도 쓰지 않음
