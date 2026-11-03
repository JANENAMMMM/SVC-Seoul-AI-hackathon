"""4단계: 상위 식당마다 Google Place Details (New)로 리뷰와 AI 리뷰 요약을 받는다.

- reviews: 관련도순 최대 5개. 리뷰마다 원문 언어(originalText.languageCode)가 있어
  한국어로 쓴 리뷰만 골라낼 수 있다. (한국어로 썼다 ≠ 한국인. 국적은 추정하지 않는다.)
- reviewSummary: Gemini가 전체 리뷰를 요약한 문장. 어떤 리뷰를 쓸지 고르는 옵션은 없다.
두 필드 모두 Enterprise + Atmosphere 등급이라 상위 몇 곳에만 호출한다.
리뷰를 화면에 보여줄 때는 작성자 표기(author)와 링크를 함께 보여줘야 한다.
문서: https://developers.google.com/maps/documentation/places/web-service/place-details
"""

from typing import Any, Optional

import httpx
from pydantic import BaseModel

from .google_places import Restaurant, _api_key, parse_place

ENDPOINT = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = "reviews,reviewSummary"

# 저장된 place_id로 화면 표시용 정보를 다시 받을 때 쓰는 필드 (리뷰 제외 = Enterprise 등급)
DISPLAY_FIELDS = (
    "id,displayName,location,primaryType,rating,userRatingCount,priceLevel,"
    "regularOpeningHours,googleMapsUri"
)


class Review(BaseModel):
    rating: Optional[float] = None
    text: str = ""  # 요청 언어(ko)로 받은 본문. 번역됐을 수 있음
    original_text: str = ""
    original_language: Optional[str] = None  # BCP-47, 예: "ko", "en", "vi"
    author: Optional[str] = None
    author_uri: Optional[str] = None
    publish_time: Optional[str] = None
    relative_time: Optional[str] = None
    maps_url: Optional[str] = None

    @property
    def is_korean(self) -> bool:
        return (self.original_language or "").lower().split("-")[0] == "ko"


class PlaceReviews(BaseModel):
    summary: Optional[str] = None
    summary_disclosure: Optional[str] = None  # "Summarized with Gemini" 표기
    reviews_uri: Optional[str] = None
    reviews: list[Review] = []

    @property
    def korean_reviews(self) -> list[Review]:
        return [r for r in self.reviews if r.is_korean]


def _text(raw: Optional[dict[str, Any]]) -> tuple[str, Optional[str]]:
    raw = raw or {}
    return raw.get("text", ""), raw.get("languageCode")


def parse_details(raw: dict[str, Any]) -> PlaceReviews:
    reviews = []
    for r in raw.get("reviews", []):
        text, _ = _text(r.get("text"))
        original, original_lang = _text(r.get("originalText"))
        author = r.get("authorAttribution") or {}
        reviews.append(
            Review(
                rating=r.get("rating"),
                text=text,
                original_text=original or text,
                original_language=original_lang,
                author=author.get("displayName"),
                author_uri=author.get("uri"),
                publish_time=r.get("publishTime"),
                relative_time=r.get("relativePublishTimeDescription"),
                maps_url=r.get("googleMapsUri"),
            )
        )
    summary = raw.get("reviewSummary") or {}
    summary_text, _ = _text(summary.get("text"))
    disclosure, _ = _text(summary.get("disclosureText"))
    return PlaceReviews(
        summary=summary_text or None,
        summary_disclosure=disclosure or None,
        reviews_uri=summary.get("reviewsUri"),
        reviews=reviews,
    )


def _get_details(
    place_id: str, field_mask: str, language: str, client: Optional[httpx.Client]
) -> dict[str, Any]:
    headers = {"X-Goog-Api-Key": _api_key(), "X-Goog-FieldMask": field_mask}
    owns_client = client is None
    http = client or httpx.Client(timeout=30)
    try:
        response = http.get(
            ENDPOINT.format(place_id=place_id), params={"languageCode": language}, headers=headers
        )
        response.raise_for_status()
    finally:
        if owns_client:
            http.close()
    return response.json()


def fetch_reviews(
    place_id: str, language: str = "ko", client: Optional[httpx.Client] = None
) -> PlaceReviews:
    """장소 상세 1회 = Enterprise + Atmosphere 등급 1회."""
    return parse_details(_get_details(place_id, FIELD_MASK, language, client))


class PlaceDisplay(BaseModel):
    restaurant: Restaurant
    maps_url: Optional[str] = None
    reviews: Optional[PlaceReviews] = None


def fetch_place_for_display(
    place_id: str,
    with_reviews: bool = False,
    language: str = "ko",
    client: Optional[httpx.Client] = None,
) -> PlaceDisplay:
    """저장된 place_id로 화면 표시용 정보를 다시 받는다 (저장된 일정 보기 등).

    호출 1회. with_reviews=False면 Enterprise, True면 리뷰까지 받아 Enterprise + Atmosphere 등급.
    받은 값은 화면에 보여주고 저장하지 않는다.
    """
    mask = DISPLAY_FIELDS + ("," + FIELD_MASK if with_reviews else "")
    raw = _get_details(place_id, mask, language, client)
    return PlaceDisplay(
        restaurant=parse_place({"id": place_id, **raw}),
        maps_url=raw.get("googleMapsUri"),
        reviews=parse_details(raw) if with_reviews else None,
    )
