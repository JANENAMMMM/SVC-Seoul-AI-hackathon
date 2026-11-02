"""1~6단계 전체 흐름. 관광지 목록을 받아 관광지마다 추천 식당 5곳과 리뷰 신호를 만든다.

1. Google Nearby Search로 관광지 주변 식당 20개
2~3. 규칙으로 거르고 점수로 상위 5개 (ranking.py)
4. 상위 5곳마다 Google Place Details로 리뷰(최대 5개) + AI 리뷰 요약
5. 한국어 원문 리뷰 + 요약에서 키워드 태그·경고 (keywords.py)
6. 결과 저장

외부 호출 결과는 data/restaurants/ 아래에 캐시해서 다시 돌릴 때 API를 부르지 않는다.
(data/는 .gitignore 대상. Google 데이터는 로컬 개발·시연용으로만 보관한다.
 Google Maps Platform 약관의 캐싱·AI 활용 조건은 별도 확인 필요.)
"""

import json
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel

from .google_places import Restaurant, search_nearby_restaurants
from .google_reviews import PlaceReviews, Review, fetch_reviews
from .keywords import Signals, analyze
from .preferences import FoodPreference
from .ranking import ALL_DAYS, DEFAULT_MEAL_TIMES, build_candidates, select_top

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "restaurants"

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
    korean_reviews: list[Review]  # 그중 한국어 원문 리뷰
    signals: Signals  # 한국어 리뷰 + 요약에서 뽑은 태그·경고


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


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _cached_google(
    attraction: Attraction,
    radius_m: float,
    included_types: tuple[str, ...],
    cache_dir: Path,
    refresh: bool,
    google_search: GoogleSearch,
) -> list[Restaurant]:
    suffix = "" if included_types == ("restaurant",) else "_" + "-".join(included_types)
    path = cache_dir / "google" / f"{attraction.id}{suffix}.json"
    if path.exists() and not refresh:
        return [Restaurant.model_validate(r) for r in _read_json(path)]
    found = google_search(
        attraction.lat, attraction.lng, radius_m=radius_m, included_types=included_types
    )
    _write_json(path, [r.model_dump() for r in found])
    return found


def _cached_reviews(
    place_id: str, cache_dir: Path, refresh: bool, review_fetch: ReviewFetch
) -> PlaceReviews:
    path = cache_dir / "google_reviews" / f"{place_id}.json"
    if path.exists() and not refresh:
        return PlaceReviews.model_validate(_read_json(path))
    reviews = review_fetch(place_id)
    _write_json(path, reviews.model_dump())
    return reviews


def review_info(place: PlaceReviews, pref: FoodPreference) -> ReviewInfo:
    korean = place.korean_reviews
    texts = [r.original_text for r in korean] + ([place.summary] if place.summary else [])
    return ReviewInfo(
        summary=place.summary,
        summary_disclosure=place.summary_disclosure,
        reviews_uri=place.reviews_uri,
        returned_count=len(place.reviews),
        korean_reviews=korean,
        signals=analyze(texts, pref),
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
    cache_dir: Path = DEFAULT_CACHE_DIR,
    refresh: bool = False,
    google_search: GoogleSearch = search_nearby_restaurants,
    review_fetch: ReviewFetch = fetch_reviews,
) -> CollectResult:
    results = []
    for attraction in attractions:
        # 1단계: 반경 검색 1회 (캐시 있으면 호출 안 함)
        found = _cached_google(
            attraction, radius_m, ("restaurant",), cache_dir, refresh, google_search
        )
        origin = (attraction.lat, attraction.lng)

        # 2~3단계: 거르기 + 점수
        candidates = build_candidates(found, pref, origin, country, days, meal_times)
        # 한식이 필요한데 20개 안에 한식당이 없으면 한식당만 1회 더 검색
        if pref.needs_korean and not any(
            c.cuisine.is_korean and c.excluded_reason is None for c in candidates
        ):
            korean = _cached_google(
                attraction, radius_m, ("korean_restaurant",), cache_dir, refresh, google_search
            )
            candidates = build_candidates(found + korean, pref, origin, country, days, meal_times)
        top = select_top(candidates, pref)

        # 4~5단계: 상위 식당마다 리뷰 조회 1회 + 키워드 태그
        recommended = []
        for c in top:
            r = c.restaurant
            info = None
            if with_reviews:
                info = review_info(_cached_reviews(r.place_id, cache_dir, refresh, review_fetch), pref)
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


def save_result(result: CollectResult, path: Path) -> None:
    """6단계: 결과를 JSON으로 저장."""
    _write_json(path, result.model_dump())
