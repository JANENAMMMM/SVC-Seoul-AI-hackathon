"""일정 엔진 입출력 스키마."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src.profile.schema import ParentProfile

Mode = Literal["standard", "short", "full"]
Pace = Literal["slower", "normal", "faster"]


class LatLng(BaseModel):
    lat: float
    lng: float


class DayWindow(BaseModel):
    start: str = "09:00"
    end: str = "21:00"


class PlanState(BaseModel):
    """재생성에 필요한 상태. 서버는 저장하지 않고 클라이언트가 다시 보낸다."""

    pins: dict[str, int] = Field(default_factory=dict)
    mode_overrides: dict[str, Mode] = Field(default_factory=dict)
    korean_need_override: str | None = None
    pace: Pace = "normal"
    weights: dict[str, float] = Field(default_factory=dict)
    meal_pins: dict[str, str] = Field(default_factory=dict)
    excluded_restaurants: list[str] = Field(default_factory=list)
    walk_limit_override: int | None = None
    feedback_log: list[str] = Field(default_factory=list)  # 승인된 조정 요약(HITL). 다음 자연어 해석의 맥락


class PlanRequest(BaseModel):
    travelers: list[ParentProfile] = Field(min_length=1)
    place_ids: list[str] = Field(min_length=1)
    days: int = Field(ge=1, le=14)
    start_date: date | None = None
    start_point: LatLng | None = None
    day_window: DayWindow | None = None
    state: PlanState = Field(default_factory=PlanState)


class RestaurantPick(BaseModel):
    place_id: str
    name: str
    primary_type: str | None = None
    rating: float | None = None
    rating_count: int | None = None
    is_korean: bool = False
    is_local: bool = False
    hours_unknown: bool = False
    distance_km: float | None = None
    travel_min: int | None = None
    transport: str | None = None
    venue_type: str | None = None
    ingredient_tags: list[str] | None = None
    tag_confidence: str | None = None
    tag_evidence: list | str | None = None


class Stop(BaseModel):
    type: Literal["base", "attraction", "meal", "rest", "move"]
    start: str | None = None
    end: str | None = None
    place_id: str | None = None
    name: str | None = None
    mode: Mode | None = None
    mode_name: str | None = None
    walk_min: int | None = None
    note: str | None = None
    meal: Literal["lunch", "dinner"] | None = None
    fixed: bool = False
    restaurant: RestaurantPick | None = None
    minutes: int | None = None
    transport: Literal["walk", "taxi"] | None = None
    reason: str | None = None


class DayPlan(BaseModel):
    day: int
    weekday: str | None = None
    stops: list[Stop] = Field(default_factory=list)
    difficulty: int | None = None
    total_walk_min: int = 0
    max_continuous_walk_min: int = 0


class PackageScore(BaseModel):
    peak: int
    mean: float


class Unscheduled(BaseModel):
    place_id: str
    reason: str


class Itinerary(BaseModel):
    plan_id: str
    request: PlanRequest
    days: list[DayPlan]
    package: PackageScore | None = None
    unscheduled: list[Unscheduled] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    review_comment: str | None = None
    state: PlanState


class LightenDay(BaseModel):
    op: Literal["lighten_day"]
    day: int


class AddPlace(BaseModel):
    op: Literal["add_place"]
    place_id: str
    day: int | None = None


class RemovePlace(BaseModel):
    op: Literal["remove_place"]
    place_id: str


class MovePlace(BaseModel):
    op: Literal["move_place"]
    place_id: str
    day: int


class SetMode(BaseModel):
    op: Literal["set_mode"]
    place_id: str
    mode: Mode


class MoreKoreanMeals(BaseModel):
    op: Literal["more_korean_meals"]


class SetPace(BaseModel):
    op: Literal["set_pace"]
    pace: Pace


class SwapRestaurant(BaseModel):
    op: Literal["swap_restaurant"]
    day: int
    meal: Literal["lunch", "dinner"]


class AdjustWalkLimit(BaseModel):
    op: Literal["adjust_walk_limit"]
    direction: Literal["more", "less"]


EditCommand = Annotated[
    LightenDay | AddPlace | RemovePlace | MovePlace | SetMode | MoreKoreanMeals | SetPace
    | SwapRestaurant | AdjustWalkLimit,
    Field(discriminator="op"),
]


class RefineRequest(BaseModel):
    itinerary: Itinerary
    commands: list[EditCommand] = Field(default_factory=list)
    feedback: str | None = None


class RefineResponse(BaseModel):
    itinerary: Itinerary
    applied_commands: list[EditCommand] = Field(default_factory=list)
    change_summary: str = ""
    clarification: str | None = None
