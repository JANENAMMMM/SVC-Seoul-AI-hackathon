"""부모님 음식 취향 질문(4문항)의 답. 프로필 화면에서 받은 값을 그대로 담는다.

1. 처음 접하는 현지 음식을 얼마나 즐기시나요?          -> local_food
2. 해외여행 중 한식이 얼마나 필요한가요?                -> korean_need
3. 드시지 못하거나 피하시는 식재료 (복수 선택)          -> avoid_ingredients, avoid_other
4. 이용하실 수 있는 식사 장소 (복수 선택)               -> venues
"잘 모르겠어요"는 "unknown"으로 받고, 필터를 걸지 않는 중간값으로 처리한다.
"""

from typing import Literal

from pydantic import BaseModel

LocalFood = Literal["familiar", "mixed", "adventurous", "unknown"]
KoreanNeed = Literal["daily", "every_2_3_days", "occasional", "none", "unknown"]
Ingredient = Literal["seafood", "pork", "dairy", "nuts"]
Venue = Literal["restaurant", "street_food", "unknown"]


class FoodPreference(BaseModel):
    local_food: LocalFood = "unknown"
    korean_need: KoreanNeed = "unknown"
    avoid_ingredients: list[Ingredient] = []
    avoid_other: list[str] = []  # "기타: 직접 입력"
    venues: list[Venue] = ["unknown"]

    @property
    def needs_korean(self) -> bool:
        """상위 5개에 한식당을 꼭 넣어야 하는지. 2~3일에 한 번 이상이면 넣는다."""
        return self.korean_need in ("daily", "every_2_3_days")

    @property
    def street_food_ok(self) -> bool:
        """길거리 음식점을 골랐거나 모르면 허용."""
        return "street_food" in self.venues or "unknown" in self.venues
