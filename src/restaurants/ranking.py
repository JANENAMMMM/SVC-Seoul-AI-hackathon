"""2~3단계: 규칙으로 거르고 점수로 정렬해 상위 5개를 고른다. LLM을 쓰지 않는다.

2. 거르기: 대표 타입이 음식점이 아닌 곳(호텔 등), 이름에 쿠킹 클래스가 있는 곳, 식사 시간에 문을 닫는 곳, 부모님이 피하는 해산물 전문점 제외
3. 정렬: 평점과 리뷰 수를 함께 반영한 베이지안 평균 + 현지 음식 선호 보정
   한식이 필요하면 상위 5개에 한식당 1곳을 반드시 넣는다 (한식 여부는 Candidate.is_korean_final 기준).

저장 규칙: 이름·평점·리뷰 수·영업시간 같은 데이터와 점수·제외 사유 같은 계산값은 메모리에서만 쓰고
저장하지 않는다.
"""

import math
import re
from typing import Optional

from pydantic import BaseModel

from .cuisine import CuisineInfo, classify
from .google_places import OpeningPeriod, Restaurant
from .korean_judgment import KoreanCheck
from .preferences import FoodPreference

MINUTES_PER_DAY = 24 * 60
MINUTES_PER_WEEK = 7 * MINUTES_PER_DAY

DEFAULT_MEAL_TIMES = ("12:00", "18:30")  # 점심·저녁 기준 시각
ALL_DAYS = frozenset(range(7))  # 0=일요일 ~ 6=토요일 (Google 영업시간과 같은 기준)

# 베이지안 평균: 리뷰가 적은 고평점 식당이 위로 튀지 않게 PRIOR_COUNT개의 평균 평점을 섞는다.
PRIOR_COUNT = 50
DEFAULT_PRIOR_RATING = 4.0

# 질문 1(현지 음식 선호)에 따른 점수 보정. 팀 가정값.
LOCAL_FOOD_ADJUST = {"familiar": -0.15, "mixed": 0.0, "adventurous": 0.15, "unknown": 0.0}

TOP_N = 5

# 대표 타입이 음식점 계열인 곳만 남긴다. 검색은 "식당 타입이 포함된 곳"이라
# 대표 타입이 호텔·리조트·상점인 곳도 섞여 들어온다 (예: resort_hotel, hotel, grocery_store).
FOOD_PRIMARY_TYPES = frozenset(
    {
        "restaurant", "bistro", "snack_bar", "noodle_shop", "food_court", "steak_house", "diner",
        # 식사가 되는 가게. 동남아는 반미(sandwich_shop) 가게가 많아서 꼭 포함해야 한다
        "sandwich_shop", "kebab_shop", "hot_dog_stand", "salad_shop", "deli",
        # 술집이지만 식사가 주인 곳
        "gastropub", "bar_and_grill",
    }
)


def is_food_place(primary_type: Optional[str]) -> bool:
    """대표 타입을 모르면 거르지 않는다."""
    if not primary_type:
        return True
    return primary_type in FOOD_PRIMARY_TYPES or primary_type.endswith("_restaurant")


# 대표 타입은 restaurant인데 실제로는 쿠킹 클래스인 곳이 있다 (예: "Tuong cooking class hoi an").
# 식당이 아니라 체험 프로그램이라 이름에 아래 표현이 있으면 제외한다. 리뷰는 보지 않는다
# (진짜 식당 리뷰에도 "쿠킹클래스가 있어서 붐빈다" 같은 언급이 나온다).
COOKING_CLASS_PATTERN = re.compile(
    r"cooking\s*class|cooking\s*school|cookery|쿠킹\s*클래스|쿠킹\s*스쿨|요리\s*(교실|학교|수업)|lớp\s*học\s*nấu\s*ăn",
    re.IGNORECASE,
)


def is_cooking_class(name: str) -> bool:
    return bool(COOKING_CLASS_PATTERN.search(name))


class Candidate(BaseModel):
    restaurant: Restaurant
    cuisine: CuisineInfo
    distance_m: Optional[int] = None
    score: float = 0.0
    hours_unknown: bool = False  # 영업시간 정보가 없어 시간 필터를 적용하지 못함
    excluded_reason: Optional[str] = None
    # Claude 한식 판단 (korean_check.py, 선택 기능). 판단하지 않았으면 None.
    # cuisine(원본 분류)은 건드리지 않고 이 값을 옆에 붙인다.
    korean_check: Optional["KoreanCheck"] = None

    @property
    def is_korean_final(self) -> bool:
        """한식 여부 최종값. Claude 판단이 있으면 그것을, 없으면 Google 분류 기준(cuisine.is_korean)을 쓴다.

        Claude가 uncertain이면 한식이 아닌 것으로 처리한다.
        """
        if self.korean_check is None:
            return self.cuisine.is_korean
        return self.korean_check.verdict == "korean"


def _minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def _period_contains(period: OpeningPeriod, minute_of_week: int) -> bool:
    start = period.open_day * MINUTES_PER_DAY + _minutes(period.open_time)
    if period.close_day is None or period.close_time is None:
        return True  # close가 없으면 24시간 영업
    end = period.close_day * MINUTES_PER_DAY + _minutes(period.close_time)
    if end <= start:  # 자정·주말을 넘겨 끝나는 영업
        end += MINUTES_PER_WEEK
    return start <= minute_of_week < end or start <= minute_of_week + MINUTES_PER_WEEK < end


def is_open_at(restaurant: Restaurant, day: int, hhmm: str) -> bool:
    minute_of_week = day * MINUTES_PER_DAY + _minutes(hhmm)
    return any(_period_contains(p, minute_of_week) for p in restaurant.opening_periods)


def open_for_meals(
    restaurant: Restaurant,
    days: frozenset[int] = ALL_DAYS,
    meal_times: tuple[str, ...] = DEFAULT_MEAL_TIMES,
) -> bool:
    """여행하는 모든 요일에 식사 시각 중 하나 이상 문을 여는지."""
    return all(any(is_open_at(restaurant, d, t) for t in meal_times) for d in days)


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """하버사인 직선거리(m)."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)))


def bayesian_rating(rating: Optional[float], count: Optional[int], prior: float) -> float:
    if rating is None or not count:
        return prior
    return (count * rating + PRIOR_COUNT * prior) / (count + PRIOR_COUNT)


def build_candidates(
    restaurants: list[Restaurant],
    pref: FoodPreference,
    origin: Optional[tuple[float, float]] = None,
    country: Optional[str] = None,
    days: frozenset[int] = ALL_DAYS,
    meal_times: tuple[str, ...] = DEFAULT_MEAL_TIMES,
) -> list[Candidate]:
    """2단계 거르기 + 3단계 점수 매기기. 제외된 곳도 excluded_reason과 함께 돌려준다."""
    rated = [r.rating for r in restaurants if r.rating is not None]
    prior = sum(rated) / len(rated) if rated else DEFAULT_PRIOR_RATING

    candidates = []
    seen: set[str] = set()
    for r in restaurants:
        if r.place_id in seen:
            continue
        seen.add(r.place_id)
        cuisine = classify(r.primary_type, [], country)
        c = Candidate(
            restaurant=r,
            cuisine=cuisine,
            distance_m=distance_m(*origin, r.lat, r.lng) if origin else None,
            hours_unknown=not r.opening_periods,
        )
        if not is_food_place(r.primary_type):
            c.excluded_reason = f"음식점이 아님 (대표 타입: {r.primary_type})"
        elif is_cooking_class(r.name):
            c.excluded_reason = "쿠킹 클래스 (이름에 cooking class 등 포함)"
        elif "seafood" in pref.avoid_ingredients and cuisine.has_seafood_type:
            c.excluded_reason = "해산물 전문점 (해산물을 피하심)"
        elif r.opening_periods and not open_for_meals(r, days, meal_times):
            c.excluded_reason = "식사 시간에 문을 닫는 날이 있음"

        c.score = bayesian_rating(r.rating, r.rating_count, prior)
        if cuisine.is_local:
            c.score += LOCAL_FOOD_ADJUST[pref.local_food]
        candidates.append(c)
    return candidates


def select_top(candidates: list[Candidate], pref: FoodPreference, n: int = TOP_N) -> list[Candidate]:
    """점수순 상위 n개. 한식이 필요한데 없으면 마지막 자리를 가장 높은 한식당으로 바꾼다."""
    kept = sorted(
        (c for c in candidates if c.excluded_reason is None), key=lambda c: c.score, reverse=True
    )
    top = kept[:n]
    if pref.needs_korean and top and not any(c.is_korean_final for c in top):
        best_korean = next((c for c in kept[n:] if c.is_korean_final), None)
        if best_korean:
            top = top[: n - 1] + [best_korean]
    return top
