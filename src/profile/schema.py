"""부모님 프로필 입력/출력 스키마."""

from typing import Literal

from pydantic import BaseModel

Gender = Literal["female", "male"]
WalkingDuration = Literal["under_15min", "15_30min", "30_60min", "1_2hour", "over_2hour"]

# src/restaurants/preferences.py (feat/restaurant-collector 브랜치, 아직 머지 안 됨)의
# FoodPreference와 같은 필드명·타입·기본값. 그 브랜치는 건드리지 않고 여기서 그대로
# 미러링해서, 나중에 머지돼도 바로 호환되게 한다.
LocalFood = Literal["familiar", "mixed", "adventurous", "unknown"]
KoreanNeed = Literal["daily", "every_2_3_days", "occasional", "none", "unknown"]
Ingredient = Literal["seafood", "pork", "dairy", "nuts"]
Venue = Literal["restaurant", "street_food", "unknown"]


class WalkingSpeed(BaseModel):
    """나이·성별 기준 보행속도.

    국내 보행속도 연구(한국인 다기관 등록 연구, 압력 기반 보행 분석)의
    연령대(5세 단위)·성별 평균값 표를 그대로 쓴 "건강한 인구" 기준값이다.
    """

    age_band: str
    base_speed_mps: float
    # TODO: 계단 오르기·연속보행 가능 시간 같은 생활형 질문이 추가되면,
    # 여기에 base_speed_mps를 깎아 "limited" 등급까지 나누는 보정 로직을 끼워 넣는다.
    # 지금은 생활형 질문이 없어 base_speed_mps를 그대로 기준 속도로 쓴다.


class ParentProfileInput(BaseModel):
    """설문에서 그대로 받는 원본 응답.

    walking_duration은 "잘 모르겠어요" 선택 시 None. 음식 취향 4문항은 FoodPreference와
    같은 기본값 규칙을 따른다 — "잘 모르겠어요"는 null이 아니라 "unknown"(또는
    venues의 경우 ["unknown"])으로, "없어요"는 빈 리스트로 받는다.
    """

    age: int
    gender: Gender
    walking_duration: WalkingDuration | None = None

    local_food: LocalFood = "unknown"
    korean_need: KoreanNeed = "unknown"
    avoid_ingredients: list[Ingredient] = []
    avoid_other: list[str] = []
    venues: list[Venue] = ["unknown"]


class ParentProfile(BaseModel):
    """추천 로직에 넘길 정규화된 부모님 프로필.

    walking_speed는 age·gender로 계산한 파생값이다(보행속도 표가 50세부터
    시작해서, 50세 미만이면 None). 나머지 필드는 ParentProfileInput을 그대로 옮긴 것이다.
    """

    age: int
    gender: Gender
    walking_speed: WalkingSpeed | None
    walking_duration: WalkingDuration | None

    local_food: LocalFood
    korean_need: KoreanNeed
    avoid_ingredients: list[Ingredient]
    avoid_other: list[str]
    venues: list[Venue]
