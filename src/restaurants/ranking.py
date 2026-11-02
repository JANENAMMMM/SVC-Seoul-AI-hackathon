"""2~3단계: 규칙으로 거르고 점수로 정렬해 상위 5개를 고른다. LLM을 쓰지 않는다.

2. 거르기: 식사 시간에 문을 닫는 곳, 부모님이 피하는 해산물 전문점 제외
3. 정렬: 평점과 리뷰 수를 함께 반영한 베이지안 평균 + 현지 음식 선호 보정
   한식이 필요하면 상위 5개에 한식당 1곳을 반드시 넣는다.
"""

import math
from typing import Optional

from pydantic import BaseModel

from .cuisine import CuisineInfo, classify
from .google_places import OpeningPeriod, Restaurant
from .preferences import FoodPreference

MINUTES_PER_DAY = 24 * 60
MINUTES_PER_WEEK = 7 * MINUTES_PER_DAY

DEFAULT_MEAL_TIMES = ("12:00", "18:30")  # 점심·저녁 기준 시각
ALL_DAYS = frozenset(range(7))  # 0=일요일 ~ 6=토요일 (Google 영업시간과 같은 기준)

# 베이지안 평균: 리뷰가 적은 고평점 식당이 위로 튀지 않게 PRIOR_COUNT개의 평균 평점을 섞는다.
PRIOR_COUNT = 50
DEFAULT_PRIOR_RATING = 4.0

# 질문 1(현지 음식 선호)에 따른 점수 보정. 팀 가정값.
LOCAL_FOOD_ADJUST = {"familiar": -0.15, "mixed": 0.0, "adventurous": 0.1, "unknown": 0.0}

TOP_N = 5


class Candidate(BaseModel):
    restaurant: Restaurant
    cuisine: CuisineInfo
    distance_m: Optional[int] = None
    score: float = 0.0
    hours_unknown: bool = False  # 영업시간 정보가 없어 시간 필터를 적용하지 못함
    excluded_reason: Optional[str] = None


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
        if "seafood" in pref.avoid_ingredients and cuisine.has_seafood_type:
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
    if pref.needs_korean and top and not any(c.cuisine.is_korean for c in top):
        best_korean = next((c for c in kept[n:] if c.cuisine.is_korean), None)
        if best_korean:
            top = top[: n - 1] + [best_korean]
    return top
