"""반걸음 공유 여행 데이터 스키마 — 초안 v0 (뼈대만)

규칙
- 필드는 추가만 한다. 이름 변경·삭제 금지.
- 스키마 수정은 한 사람(재은)만 머지한다.
- 모든 탭·패널·에이전트는 Trip 하나를 읽고 쓴다. 수정할 때마다 version += 1.
- 계산값(parent_duration_min, metrics 등)은 검증 엔진만 쓴다. 에이전트·UI는 읽기만.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── 1. 부모님 프로필 · 조건 (프로필 탭) ─────────────────────────
class ParentProfile(BaseModel):
    name: str                                   # "어머니"
    answers: dict[str, str] = {}                # 생활형 질문 id → 답
    walking_grade: Literal["easy", "normal", "limited"]   # 원활/보통/불편
    walking_speed_mps: float                    # 규칙표 기본값(1.1/0.8/0.7) 또는 실측값
    speed_source: Literal["rule", "measured", "health_app"] = "rule"
    confirmed_by_parent: bool = False


class Constraints(BaseModel):
    max_continuous_walk_min: int = 20           # 팀 가정값, 프로필로 보정
    max_daily_walk_m: int = 5000
    rest_interval_m: int = 100                  # 등급별: 100(보통) / 50(불편)
    avoid_stairs: bool = False
    day_start: str = "09:00"
    day_end: str = "19:00"
    food_restrictions: list[str] = []           # ["raw", "spicy"]
    must_visit_place_ids: list[str] = []
    must_keep: list[str] = []                   # 자녀가 고른 필수 조건 키 (위 필드 이름)


# ── 2. 장소 · 일정 (현재 일정 탭) ───────────────────────────────
class Place(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    category: Literal["attraction", "restaurant", "cafe", "hotel", "other"]
    address: str = ""
    opening_hours: Optional[str] = None
    has_stairs: Optional[bool] = None           # 모르면 None
    is_korean_food: bool = False
    review_note: Optional[str] = None           # 후기 근거 한 줄 (식당 패널)
    data_quality: Literal["api", "manual", "estimated"] = "api"   # 데모용 수작업 데이터 표시


class Stop(BaseModel):
    type: Literal["stop"] = "stop"
    id: str
    place_id: str
    start: str                                  # "10:00"
    end: str
    kind: Literal["visit", "meal", "rest", "hotel"]
    must_visit: bool = False
    added_by: Literal["agent", "user", "validator"] = "agent"


class Move(BaseModel):
    type: Literal["move"] = "move"
    id: str
    from_stop_id: str
    to_stop_id: str
    mode: Literal["walk", "taxi", "car"]
    distance_m: int
    map_duration_min: int                       # 경로 API 원값 (기준 속도 = 거리 ÷ 시간)
    parent_duration_min: Optional[int] = None   # 검증 엔진이 채움
    cost_krw: int = 0                           # 택시는 거리 × 요율 추정


class Day(BaseModel):
    date: str                                   # "2026-12-03"
    density: Literal["relaxed", "normal", "packed"] = "normal"   # 촘촘도
    items: list[Stop | Move] = Field(default_factory=list)       # 시간 순서


class DayWeather(BaseModel):                    # 날씨 패널 + 더위 보정 입력
    date: str
    max_temp_c: float
    rain_prob: int
    heat_risk_hours: list[str] = []             # ["12:00-15:00"]


# ── 3. 검증 결과 (걸음 다시 재기) ────────────────────────────────
class Fix(BaseModel):
    id: str
    kind: Literal["to_taxi", "add_rest", "swap_place", "drop_item", "plan_b"]
    description: str                            # "도보 26분 → 택시"
    delta_cost_krw: int = 0
    delta_walk_min: int = 0
    applied: bool = False


class Issue(BaseModel):
    id: str
    item_id: str                                # Stop 또는 Move id
    rule: Literal["continuous_walk", "daily_walk", "rest_interval", "stairs",
                  "heat", "opening_hours", "food"]
    severity: Literal["must", "soft"]           # must = 필수 조건 위반
    message: str                                # "입구까지 도보 26분 · 계단"
    evidence: str = ""                          # "보통 등급 0.8 m/s 기준"
    fixes: list[Fix] = []


class Metrics(BaseModel):                       # 발표 핵심 지표 3개 + 보조
    violations: int
    must_visit_kept_ratio: float
    extra_cost_per_fix_krw: int
    max_continuous_walk_min: int
    parent_walk_total_min: int


class ValidationReport(BaseModel):
    trip_version: int                           # 어느 버전을 검사했는지
    issues: list[Issue]
    metrics: Metrics


# ── 4. 예산 · 부모님 의견 ───────────────────────────────────────
class CostLine(BaseModel):
    category: Literal["flight", "hotel", "taxi", "food", "ticket", "guide", "other"]
    amount_krw: int
    is_comfort_cost: bool = False               # 보정으로 생긴 '편안함 비용'
    fix_id: Optional[str] = None


class ParentFeedback(BaseModel):
    id: str
    trip_version: int
    item_id: Optional[str] = None
    channel: Literal["button", "voice"]
    value: Literal["like", "too_hard", "answer"]
    transcript: Optional[str] = None            # 음성 받아쓰기
    status: Literal["pending", "approved", "rejected"] = "pending"   # 자녀 승인


# ── 5. 최상위: 모든 탭이 공유하는 하나의 상태 ────────────────────
class Trip(BaseModel):
    id: str
    version: int = 1
    destination: str                            # GTA TravelIntent에서 이어받음
    check_in: str
    check_out: str
    budget_krw: int
    adults: int
    parents: list[ParentProfile]
    constraints: Constraints
    places: dict[str, Place] = {}               # id → Place
    days: list[Day] = []
    hotel_place_id: Optional[str] = None
    weather: list[DayWeather] = []
    validation: Optional[ValidationReport] = None
    costs: list[CostLine] = []
    feedback: list[ParentFeedback] = []
    guide_selected: bool = False
    updated_by: Literal["agent", "user", "validator", "system"] = "system"
