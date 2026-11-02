"""Google Places API (New) Nearby Search로 관광지 주변 식당을 받는다.

요청 필드는 Enterprise 등급까지만 쓴다. Atmosphere 필드(reviews, reviewSummary 등)를
하나라도 넣으면 모든 요청이 가장 비싼 등급으로 계산되므로 여기서는 받지 않는다.
문서: https://developers.google.com/maps/documentation/places/web-service/nearby-search
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"
MAX_RESULTS = 20  # Nearby Search 한 번에 받을 수 있는 최대 개수

# 1단계 정리본 기준. id·displayName·location은 다음 단계(네이버 검색, 거리, 재사용)에 필요해 추가.
# 등급: Pro = id, displayName, location, primaryType / Enterprise = 나머지
FIELDS = (
    "id",
    "displayName",
    "location",
    "primaryType",
    "rating",
    "userRatingCount",
    "priceLevel",
    "regularOpeningHours",
)
FIELD_MASK = ",".join(f"places.{name}" for name in FIELDS)

# 식사 장소가 아닌 곳은 대표 타입 기준으로 뺀다. includedPrimaryTypes=["restaurant"]로 제한하면
# korean_restaurant처럼 세부 타입이 대표인 식당이 빠질 수 있어서 제외 방식을 쓴다.
DEFAULT_EXCLUDED_PRIMARY_TYPES = (
    "cafe",
    "coffee_shop",
    "bakery",
    "dessert_shop",
    "ice_cream_shop",
    "juice_shop",
    "bar",
    "pub",
    "wine_bar",
    "cocktail_bar",
    "lounge_bar",
)


class OpeningPeriod(BaseModel):
    """day: 0=일요일 ~ 6=토요일. close가 없으면 24시간 영업으로 본다."""

    open_day: int
    open_time: str  # "HH:MM"
    close_day: Optional[int] = None
    close_time: Optional[str] = None


class Restaurant(BaseModel):
    place_id: str
    name: str
    name_language: Optional[str] = None
    lat: float
    lng: float
    primary_type: Optional[str] = None  # 음식 종류 (korean_restaurant 등)
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    price_level: Optional[str] = None  # PRICE_LEVEL_INEXPENSIVE 등 원값
    opening_periods: list[OpeningPeriod] = []  # 요일별 정기 영업시간 (regularOpeningHours)
    opening_text: list[str] = []  # 같은 필드의 요일별 문장 (화면 표시용)


def build_request_body(
    lat: float,
    lng: float,
    radius_m: float = 1000,
    included_types: tuple[str, ...] = ("restaurant",),
    excluded_primary_types: tuple[str, ...] = DEFAULT_EXCLUDED_PRIMARY_TYPES,
    max_results: int = MAX_RESULTS,
    language: str = "ko",
) -> dict[str, Any]:
    if not 1 <= max_results <= MAX_RESULTS:
        raise ValueError(f"max_results는 1~{MAX_RESULTS} 사이여야 합니다: {max_results}")
    body: dict[str, Any] = {
        "includedTypes": list(included_types),
        "maxResultCount": max_results,
        "rankPreference": "POPULARITY",
        "languageCode": language,
        "locationRestriction": {
            "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": radius_m}
        },
    }
    if excluded_primary_types:
        body["excludedPrimaryTypes"] = list(excluded_primary_types)
    return body


def _hhmm(point: dict[str, Any]) -> str:
    return f"{point.get('hour', 0):02d}:{point.get('minute', 0):02d}"


def parse_place(raw: dict[str, Any]) -> Restaurant:
    """API 응답의 place 하나를 Restaurant로 바꾼다. 없는 필드는 None/빈 값으로 둔다."""
    display = raw.get("displayName") or {}
    location = raw.get("location") or {}
    hours = raw.get("regularOpeningHours") or {}

    periods = []
    for period in hours.get("periods", []):
        opened = period.get("open") or {}
        closed = period.get("close")
        periods.append(
            OpeningPeriod(
                open_day=opened.get("day", 0),
                open_time=_hhmm(opened),
                close_day=closed.get("day") if closed else None,
                close_time=_hhmm(closed) if closed else None,
            )
        )

    return Restaurant(
        place_id=raw["id"],
        name=display.get("text", ""),
        name_language=display.get("languageCode"),
        lat=location.get("latitude", 0.0),
        lng=location.get("longitude", 0.0),
        primary_type=raw.get("primaryType"),
        rating=raw.get("rating"),
        rating_count=raw.get("userRatingCount"),
        price_level=raw.get("priceLevel"),
        opening_periods=periods,
        opening_text=hours.get("weekdayDescriptions", []),
    )


@lru_cache
def _api_key() -> str:
    """환경변수가 루트 .env보다 우선한다 (supabase_client와 같은 방식)."""
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Google Places 설정이 필요합니다: GOOGLE_API_KEY. "
            ".env.example을 참고해 루트 .env를 작성하세요."
        )
    return key


def search_nearby_restaurants(
    lat: float,
    lng: float,
    radius_m: float = 1000,
    included_types: tuple[str, ...] = ("restaurant",),
    excluded_primary_types: tuple[str, ...] = DEFAULT_EXCLUDED_PRIMARY_TYPES,
    max_results: int = MAX_RESULTS,
    language: str = "ko",
    client: Optional[httpx.Client] = None,
) -> list[Restaurant]:
    """좌표 주변 식당을 최대 20개 받는다. 호출 1회 = Enterprise 등급 1회."""
    body = build_request_body(
        lat, lng, radius_m, included_types, excluded_primary_types, max_results, language
    )
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": FIELD_MASK,
    }
    owns_client = client is None
    http = client or httpx.Client(timeout=30)
    try:
        response = http.post(ENDPOINT, json=body, headers=headers)
        response.raise_for_status()
    finally:
        if owns_client:
            http.close()
    return [parse_place(place) for place in response.json().get("places", [])]
