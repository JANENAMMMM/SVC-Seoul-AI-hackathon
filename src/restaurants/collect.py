"""전체 흐름. 관광지 목록을 받아 관광지마다 추천 식당 5곳과 한국어 리뷰 원문을 돌려준다.

1. Google Nearby Search로 관광지 주변 식당 20개
2~3. 규칙으로 거르고 점수로 상위 5개 (ranking.py)
4. 상위 5곳마다 Google Place Details로 리뷰(최대 5개) + AI 리뷰 요약, 한국어 원문 리뷰만 골라 그대로 담음
5. 결과를 돌려줌

리뷰는 가공하지 않고 원문 그대로 담는다 (키워드 태그·경고 없음). 리뷰 내용 판단은 LLM 단계의 일이다.

부모님 프로필은 받지 않는다. 해산물 기피·현지 음식 선호·한식 빈도는 일정 엔진이 이 결과를 받아 반영한다.
그래서 같은 결과를 프로필이 다른 여러 일정에 그대로 쓸 수 있다.

저장 규칙:
- 저장하지 않는다. 이름·평점·영업시간·리뷰 등 식당 데이터와 점수·분류·한식 판단 같은 계산값은
  호출한 쪽(그래프 state 등)에 돌려주기만 하고 파일·DB에 쓰지 않는다.
- 한 번 실행하는 동안만 메모리에서 같은 식당의 리뷰 중복 조회를 막는다.
- 실행이 끝난 뒤 남기는 건 place_id뿐이다. 다시 보여줄 때는 google_reviews.fetch_place_for_display로 재조회한다.
- 리뷰를 화면에 보여줄 때는 작성자를 항상 표시한다.
- 한식 판단(korean_judge)은 기본 꺼짐이다.

결과 필드 규칙 (다음 단계 LLM·화면이 어느 값을 믿을지 알 수 있게):
- 유지(Google 원본): name, lat, lng, primary_type, rating, rating_count, price_level, opening_text
- 유지(우리 분류표로 원본 타입에서 계산): cuisine_tag, is_korean, is_local — Claude 판단으로 덮어쓰지 않는다
- 붙음(우리가 계산): distance_m, score, hours_unknown
- 붙음(Claude 판단, korean_judge를 켰을 때만): korean_check, is_korean_final
- 덮어쓰는 필드는 없다.
"""

from typing import Callable, Optional

from pydantic import BaseModel

from .google_places import Restaurant, search_nearby_restaurants
from .google_reviews import PlaceReviews, Review, fetch_reviews
from .korean_check import KoreanJudge, apply_judgments
from .korean_judgment import KoreanCheck
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
    primary_type: Optional[str]  # Google 원본 대표 타입 (유지)
    cuisine_tag: str  # 원본 타입으로 계산한 팀 분류. Claude 판단으로 바뀌지 않음
    is_korean: bool  # 원본 타입 기준 한식 여부. Claude 판단으로 바뀌지 않음
    is_local: Optional[bool]
    rating: Optional[float]
    rating_count: Optional[int]
    price_level: Optional[str]
    opening_text: list[str]
    hours_unknown: bool
    distance_m: Optional[int]
    score: float
    reviews: Optional[ReviewInfo] = None
    # Claude 한식 판단 (korean_judge를 켰을 때만, 아니면 None). 원본 필드는 그대로 두고 옆에 붙는다.
    korean_check: Optional[KoreanCheck] = None
    # 한식 여부 최종값: korean_check가 있으면 verdict == "korean", 없으면 is_korean과 같다
    is_korean_final: bool = False


class AttractionResult(BaseModel):
    attraction: Attraction
    candidates_total: int
    excluded: dict[str, str]  # 식당 이름 -> 제외 이유
    restaurants: list[RecommendedRestaurant]


class CollectResult(BaseModel):
    city: str
    country: Optional[str]
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
    city: str,
    country: Optional[str] = None,
    radius_m: float = 1000,
    days: frozenset[int] = ALL_DAYS,
    meal_times: tuple[str, ...] = DEFAULT_MEAL_TIMES,
    with_reviews: bool = True,
    google_search: GoogleSearch = search_nearby_restaurants,
    review_fetch: ReviewFetch = fetch_reviews,
    korean_judge: Optional[KoreanJudge] = None,
) -> CollectResult:
    """korean_judge를 넘기면 Claude로 한식 여부를 판단해 korean_check로 붙인다.

    기본 꺼짐: 요청마다 시간·비용이 든다.
    """
    # 이번 실행 동안만 쓰는 메모리 (함수가 끝나면 사라짐). 여러 관광지에 같은 식당이 나오면 리뷰는 1회만 조회.
    reviews_seen: dict[str, PlaceReviews] = {}

    def search(attraction: Attraction, included_types: tuple[str, ...]) -> list[Restaurant]:
        return google_search(
            attraction.lat, attraction.lng, radius_m=radius_m, included_types=included_types
        )

    def candidates_for(found: list[Restaurant], attraction: Attraction, origin) -> list:
        cands = build_candidates(found, origin, country, days, meal_times)
        if korean_judge is not None:
            usable = [c.restaurant for c in cands if c.excluded_reason is None]
            apply_judgments(cands, korean_judge.judge(usable, f"{attraction.name}, {city}"))
        return cands

    results = []
    for attraction in attractions:
        # 1단계: 반경 검색 1회
        found = search(attraction, ("restaurant",))
        origin = (attraction.lat, attraction.lng)

        # 2~3단계: 거르기 + 점수
        candidates = candidates_for(found, attraction, origin)
        # 20개 안에 한식당이 없으면 한식당만 1회 더 검색 (한식을 쓸지는 일정 엔진이 정한다)
        if not any(
            c.is_korean_final and c.excluded_reason is None for c in candidates
        ):
            korean = search(attraction, ("korean_restaurant",))
            candidates = candidates_for(found + korean, attraction, origin)
        top = select_top(candidates)

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
                    korean_check=c.korean_check,
                    is_korean_final=c.is_korean_final,
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
    return CollectResult(city=city, country=country, attractions=results)
