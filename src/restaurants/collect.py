"""전체 흐름. 관광지 목록을 받아 관광지마다 추천 식당 5곳과 한국어 리뷰 원문을 돌려준다.

1. Google Nearby Search로 관광지 주변 식당 20개
2~3. 규칙으로 거르고 점수로 상위 5개 (ranking.py)
4. 상위 5곳마다 Google Place Details로 리뷰(최대 5개) + AI 리뷰 요약, 한국어 원문 리뷰만 골라 그대로 담음
5. 결과를 돌려줌

리뷰는 가공하지 않는다 (키워드 태그·경고 없음). 리뷰로 콘텐츠를 만드는 건
Google 약관 3.2.3(c)에 걸릴 수 있어서, 리뷰 판단은 LLM 단계에서 원문으로 한다.

저장하지 않는다 (Google Maps Platform 약관 3.2.3(a)(b): place_id 외 콘텐츠는 캐시·저장 불가).
- 결과는 호출한 쪽(그래프 state 등)에 돌려주기만 하고 파일·DB에 쓰지 않는다.
- 한 번 실행하는 동안만 메모리에서 같은 식당의 리뷰 중복 조회를 막는다.
- 실행이 끝난 뒤 남겨야 하는 건 place_id뿐. 다시 보여줄 때는 google_reviews.fetch_place_for_display로 재조회.
"""

from typing import Callable, Optional

from pydantic import BaseModel

from .google_places import Restaurant, search_nearby_restaurants
from .google_reviews import PlaceReviews, Review, fetch_reviews
from .preferences import FoodPreference
from .ranking import ALL_DAYS, DEFAULT_MEAL_TIMES, build_candidates, select_top

GoogleSearch = Callable[..., list[Restaurant]]
ReviewFetch = Callable[[str], PlaceReviews]


class Attraction(BaseModel):
    id: str
    name: str
    lat: float
    lng: float


class ReviewInfo(BaseModel):
    summary: Optional[str]  # Gemini 리뷰 요약 (화면에 summary_disclosure와 함께 표시)
    summary_disclosure: Optional[str]
    reviews_uri: Optional[str]
    returned_count: int  # Google이 준 리뷰 수 (최대 5)
    korean_reviews: list[Review]  # 그중 원문이 한국어인 리뷰 (원문 그대로, 작성자 포함)


class RecommendedRestaurant(BaseModel):
    place_id: str
    name: str
    lat: float
    lng: float
    primary_type: Optional[str]
    cuisine_tag: str
    is_korean: bool
    is_local: Optional[bool]
    rating: Optional[float]
    rating_count: Optional[int]
    price_level: Optional[str]
    opening_text: list[str]
    hours_unknown: bool
    distance_m: Optional[int]
    score: float
    reviews: Optional[ReviewInfo] = None


class AttractionResult(BaseModel):
    attraction: Attraction
    candidates_total: int
    excluded: dict[str, str]  # 식당 이름 -> 제외 이유
    restaurants: list[RecommendedRestaurant]


class CollectResult(BaseModel):
    city: str
    country: Optional[str]
    preference: FoodPreference
    attractions: list[AttractionResult]


def review_info(place: PlaceReviews) -> ReviewInfo:
    return ReviewInfo(
        summary=place.summary,
        summary_disclosure=place.summary_disclosure,
        reviews_uri=place.reviews_uri,
        returned_count=len(place.reviews),
        korean_reviews=place.korean_reviews,
    )


def collect(
    attractions: list[Attraction],
    pref: FoodPreference,
    city: str,
    country: Optional[str] = None,
    radius_m: float = 1000,
    days: frozenset[int] = ALL_DAYS,
    meal_times: tuple[str, ...] = DEFAULT_MEAL_TIMES,
    with_reviews: bool = True,
    google_search: GoogleSearch = search_nearby_restaurants,
    review_fetch: ReviewFetch = fetch_reviews,
) -> CollectResult:
    # 이번 실행 동안만 쓰는 메모리 (함수가 끝나면 사라짐). 여러 관광지에 같은 식당이 나오면 리뷰는 1회만 조회.
    reviews_seen: dict[str, PlaceReviews] = {}

    def search(attraction: Attraction, included_types: tuple[str, ...]) -> list[Restaurant]:
        return google_search(
            attraction.lat, attraction.lng, radius_m=radius_m, included_types=included_types
        )

    results = []
    for attraction in attractions:
        # 1단계: 반경 검색 1회
        found = search(attraction, ("restaurant",))
        origin = (attraction.lat, attraction.lng)

        # 2~3단계: 거르기 + 점수
        candidates = build_candidates(found, pref, origin, country, days, meal_times)
        # 한식이 필요한데 20개 안에 한식당이 없으면 한식당만 1회 더 검색
        if pref.needs_korean and not any(
            c.cuisine.is_korean and c.excluded_reason is None for c in candidates
        ):
            korean = search(attraction, ("korean_restaurant",))
            candidates = build_candidates(found + korean, pref, origin, country, days, meal_times)
        top = select_top(candidates, pref)

        # 4~5단계: 상위 식당마다 리뷰 조회 1회 + 키워드 태그
        recommended = []
        for c in top:
            r = c.restaurant
            info = None
            if with_reviews:
                if r.place_id not in reviews_seen:
                    reviews_seen[r.place_id] = review_fetch(r.place_id)
                info = review_info(reviews_seen[r.place_id])
            recommended.append(
                RecommendedRestaurant(
                    place_id=r.place_id,
                    name=r.name,
                    lat=r.lat,
                    lng=r.lng,
                    primary_type=r.primary_type,
                    cuisine_tag=c.cuisine.tag,
                    is_korean=c.cuisine.is_korean,
                    is_local=c.cuisine.is_local,
                    rating=r.rating,
                    rating_count=r.rating_count,
                    price_level=r.price_level,
                    opening_text=r.opening_text,
                    hours_unknown=c.hours_unknown,
                    distance_m=c.distance_m,
                    score=round(c.score, 3),
                    reviews=info,
                )
            )

        results.append(
            AttractionResult(
                attraction=attraction,
                candidates_total=len(candidates),
                excluded={
                    c.restaurant.name: c.excluded_reason for c in candidates if c.excluded_reason
                },
                restaurants=recommended,
            )
        )
    return CollectResult(city=city, country=country, preference=pref, attractions=results)
