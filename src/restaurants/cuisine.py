"""Google Places 장소 타입을 팀 음식 분류로 바꾸는 규칙. LLM을 쓰지 않는다.

타입 목록: https://developers.google.com/maps/documentation/places/web-service/place-types (Table A)

타입 문자열을 우리 분류표로 바꾸는 순수 계산이고 아무것도 저장하지 않는다.
"""

from typing import Literal, Optional

from pydantic import BaseModel

CuisineTag = Literal[
    "korean",
    "southeast_asian",
    "seafood",
    "japanese",
    "chinese",
    "other_asian",
    "western",
    "cafe_dessert",
    "other",
]

TYPE_TO_CUISINE: dict[str, CuisineTag] = {
    # 한식
    "korean_restaurant": "korean",
    "korean_barbecue_restaurant": "korean",
    # 동남아
    "vietnamese_restaurant": "southeast_asian",
    "thai_restaurant": "southeast_asian",
    "malaysian_restaurant": "southeast_asian",
    "indonesian_restaurant": "southeast_asian",
    "filipino_restaurant": "southeast_asian",
    "cambodian_restaurant": "southeast_asian",
    "burmese_restaurant": "southeast_asian",
    # 해산물
    "seafood_restaurant": "seafood",
    "oyster_bar_restaurant": "seafood",
    "fish_and_chips_restaurant": "seafood",
    # 일식
    "japanese_restaurant": "japanese",
    "sushi_restaurant": "japanese",
    "ramen_restaurant": "japanese",
    "japanese_curry_restaurant": "japanese",
    "japanese_izakaya_restaurant": "japanese",
    "tonkatsu_restaurant": "japanese",
    "yakiniku_restaurant": "japanese",
    "yakitori_restaurant": "japanese",
    # 중식
    "chinese_restaurant": "chinese",
    "cantonese_restaurant": "chinese",
    "chinese_noodle_restaurant": "chinese",
    "dim_sum_restaurant": "chinese",
    "dumpling_restaurant": "chinese",
    "hot_pot_restaurant": "chinese",
    "taiwanese_restaurant": "chinese",
    # 기타 아시아
    "asian_restaurant": "other_asian",
    "asian_fusion_restaurant": "other_asian",
    "indian_restaurant": "other_asian",
    "north_indian_restaurant": "other_asian",
    "south_indian_restaurant": "other_asian",
    "noodle_shop": "other_asian",
    "mongolian_barbecue_restaurant": "other_asian",
    # 양식
    "american_restaurant": "western",
    "italian_restaurant": "western",
    "french_restaurant": "western",
    "pizza_restaurant": "western",
    "steak_house": "western",
    "hamburger_restaurant": "western",
    "european_restaurant": "western",
    "mediterranean_restaurant": "western",
    "mexican_restaurant": "western",
    "spanish_restaurant": "western",
    "western_restaurant": "western",
    "bistro": "western",
    # 카페·디저트
    "cafe": "cafe_dessert",
    "coffee_shop": "cafe_dessert",
    "bakery": "cafe_dessert",
    "dessert_restaurant": "cafe_dessert",
    "dessert_shop": "cafe_dessert",
}

# 이 타입이면 해산물을 다루는 곳으로 확정 (부모님이 해산물을 피하면 제외 대상)
SEAFOOD_TYPES = frozenset(
    {"seafood_restaurant", "oyster_bar_restaurant", "sushi_restaurant", "fish_and_chips_restaurant"}
)

# 여행지 국가(ISO 3166-1 alpha-2)별 "현지 음식" 타입. 질문 1(현지 음식 선호)에 쓴다.
LOCAL_TYPES_BY_COUNTRY: dict[str, frozenset[str]] = {
    "VN": frozenset({"vietnamese_restaurant"}),
    "TH": frozenset({"thai_restaurant"}),
    "MY": frozenset({"malaysian_restaurant"}),
    "ID": frozenset({"indonesian_restaurant"}),
    "PH": frozenset({"filipino_restaurant"}),
    "KH": frozenset({"cambodian_restaurant"}),
    "MM": frozenset({"burmese_restaurant"}),
    "JP": frozenset(t for t, c in TYPE_TO_CUISINE.items() if c == "japanese"),
    "TW": frozenset({"taiwanese_restaurant"}),
    "HK": frozenset({"cantonese_restaurant", "dim_sum_restaurant"}),
}


class CuisineInfo(BaseModel):
    tag: CuisineTag
    is_korean: bool
    is_local: Optional[bool]  # 국가를 모르면 None
    has_seafood_type: bool


def classify(
    primary_type: Optional[str], types: list[str], country: Optional[str] = None
) -> CuisineInfo:
    """primaryType을 먼저 보고, 매핑이 없으면 types를 앞에서부터 본다."""
    all_types = ([primary_type] if primary_type else []) + list(types)
    tag: CuisineTag = next(
        (TYPE_TO_CUISINE[t] for t in all_types if t in TYPE_TO_CUISINE), "other"
    )
    local_types = LOCAL_TYPES_BY_COUNTRY.get(country.upper()) if country else None
    return CuisineInfo(
        tag=tag,
        is_korean=tag == "korean",
        is_local=None if local_types is None else any(t in local_types for t in all_types),
        has_seafood_type=any(t in SEAFOOD_TYPES for t in all_types),
    )
