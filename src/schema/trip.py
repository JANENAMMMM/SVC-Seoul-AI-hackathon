"""반걸음 공유 여행 데이터 스키마 — v1 (초안 v0 기반 확정본, 초안 trip_schema_draft.py는 커밋 6f09e23에 보관)

규칙
- 필드는 추가만 한다. 이름 변경·삭제 금지.
- 스키마 수정은 한 사람(재은)만 머지한다.
- 모든 탭·패널·에이전트는 Trip 하나를 읽고 쓴다. 수정할 때마다 version += 1 (저장소가 처리).
- 계산값(parent_duration_min, metrics 등)은 검증 엔진만 쓴다. 에이전트·UI는 읽기만.

draft 대비 변경 (v1)
- [추가] ParentProfile.id — profiles 테이블 키
- [추가] Move.has_stairs, Move.data_quality — 경로 API가 계단/도보시간을 못 줘서 추정·수작업 표시
- [추가] DayWeather.min_temp_c, apparent_max_temp_c, source
- [추가] Day.items 에 discriminator("type") — 파싱 안정 + TS 유니온 타입 생성
- [타입 완화] DayWeather.max_temp_c, rain_prob → Optional
  Open-Meteo 시즌 예보(D+17~)·과거 데이터는 강수확률을 주지 않아 필수면 Trip 저장이 깨짐.

v1.1 (기획 최종본 검토 P0)
- [추가] Place.onsite_walk_m / onsite_stairs, Stop.onsite_walk_m — 장소 내부 보행(주차장→입구, 사원 계단)
- [추가] PatchOp, Fix.ops — 대안을 코드가 그대로 적용할 수 있는 변경 명령
- [추가] ChangeRequest, Trip.changes — 필수 조건 위반 변경은 blocked + 대안
- [추가] DayMetrics, Metrics.per_day / map_walk_total_min — 하루 카드·전후 비교
- [추가] ValidationReport.baseline — 첫 검증(보정 전) 지표 보관
- 검증 결과 저장은 version을 올리지 않음 (storage.save_validation). validation.trip_version == version 이면 최신.
"""
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

DataQuality = Literal["api", "manual", "estimated"]


# ── 1. 부모님 프로필 · 조건 (프로필 탭) ─────────────────────────
class ParentProfile(BaseModel):
    name: str                                   # "어머니"
    answers: dict[str, str] = {}                # 생활형 질문 id → 답
    walking_grade: Literal["easy", "normal", "limited"]   # 원활/보통/불편
    walking_speed_mps: float                    # 규칙표 기본값(1.1/0.8/0.7) 또는 실측값
    speed_source: Literal["rule", "measured", "health_app"] = "rule"
    confirmed_by_parent: bool = False
    id: Optional[str] = None                    # [v1] profiles 테이블 키


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
    data_quality: DataQuality = "api"           # 데모용 수작업 데이터 표시
    onsite_walk_m: Optional[int] = None         # [v1.1] 장소 안에서 걷는 거리 (주차장→입구→관람 동선)
    onsite_stairs: Optional[bool] = None        # [v1.1] 관람 동선에 계단이 있는지 (has_stairs는 입구 기준)


class Stop(BaseModel):
    type: Literal["stop"] = "stop"
    id: str
    place_id: str
    start: str                                  # "10:00"
    end: str
    kind: Literal["visit", "meal", "rest", "hotel"]
    must_visit: bool = False
    added_by: Literal["agent", "user", "validator"] = "agent"
    onsite_walk_m: Optional[int] = None         # [v1.1] 이 방문에서만의 값 (예: 중턱까지만 관람). None이면 Place 값


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
    has_stairs: Optional[bool] = None           # [v1] 구간 내 계단/경사. 모르면 None
    data_quality: DataQuality = "api"           # [v1] 직선거리 추정이면 "estimated"


DayItem = Annotated[Union[Stop, Move], Field(discriminator="type")]


class Day(BaseModel):
    date: str                                   # "2026-12-03"
    density: Literal["relaxed", "normal", "packed"] = "normal"   # 촘촘도
    items: list[DayItem] = Field(default_factory=list)          # 시간 순서


class DayWeather(BaseModel):                    # 날씨 패널 + 더위 보정 입력
    date: str
    max_temp_c: Optional[float] = None          # [v1] Optional (시즌 예보 결측)
    rain_prob: Optional[int] = None             # [v1] Optional (과거·시즌 예보는 미제공)
    heat_risk_hours: list[str] = []             # ["12:00-15:00"]
    min_temp_c: Optional[float] = None          # [v1]
    apparent_max_temp_c: Optional[float] = None # [v1] 체감 최고 — 더위 판정 1차 근거
    source: Literal["forecast", "seasonal", "archive", "manual"] = "forecast"   # [v1]


# ── 3. 검증 결과 (걸음 다시 재기) ────────────────────────────────
class PatchOp(BaseModel):                       # [v1.1] 일정에 대한 변경 명령 1개
    op: Literal["set", "insert_after", "remove"]
    target: Literal["item", "place"] = "item"
    id: str                                     # 대상 Stop/Move id (target=place면 Place id)
    field: Optional[str] = None                 # set: 바꿀 필드 이름 ("mode")
    value: Any = None             # set: 새 값 / insert_after: 넣을 Stop·Move·Place dict


class Fix(BaseModel):
    id: str
    kind: Literal["to_taxi", "add_rest", "swap_place", "drop_item", "plan_b"]
    description: str                            # "도보 26분 → 택시"
    delta_cost_krw: int = 0
    delta_walk_min: int = 0
    applied: bool = False
    ops: list[PatchOp] = []                     # [v1.1] 적용 시 실행할 변경. 비어 있으면 설명만


class Issue(BaseModel):
    id: str
    item_id: str                                # Stop 또는 Move id
    rule: Literal["continuous_walk", "daily_walk", "rest_interval", "stairs",
                  "heat", "opening_hours", "food"]
    severity: Literal["must", "soft"]           # must = 필수 조건 위반
    message: str                                # "입구까지 도보 26분 · 계단"
    evidence: str = ""                          # "보통 등급 0.8 m/s 기준"
    fixes: list[Fix] = []


class DayMetrics(BaseModel):                    # [v1.1] 하루 카드 "천천히 걷기 40분 · 쉬는 곳 3번"
    date: str
    parent_walk_min: int
    map_walk_min: int
    max_continuous_walk_min: int
    rest_count: int
    violations: int = 0


class Metrics(BaseModel):                       # 발표 핵심 지표 3개 + 보조
    violations: int
    must_visit_kept_ratio: float
    extra_cost_per_fix_krw: int
    max_continuous_walk_min: int
    parent_walk_total_min: int
    map_walk_total_min: Optional[int] = None    # [v1.1] 같은 일정의 지도 기준 합계 (70분 → 105분 비교)
    per_day: list[DayMetrics] = []              # [v1.1]


class ValidationReport(BaseModel):
    trip_version: int                           # 어느 버전을 검사했는지
    issues: list[Issue]
    metrics: Metrics
    baseline: Optional[Metrics] = None          # [v1.1] 보정 전(첫 검증) 지표. 전후 비교 화면용


class ChangeRequest(BaseModel):                 # [v1.1] 에이전트·자녀·승인된 부모님 의견이 낸 변경
    id: str
    source: Literal["agent", "user", "parent"]
    summary: str                                # "둘째 날 오후 일정 빼기"
    ops: list[PatchOp]
    base_version: int                           # 이 버전을 보고 만든 요청
    status: Literal["applied", "blocked", "pending"] = "pending"
    blocked_by: list[str] = []                  # 깨지는 must_keep 키 ("avoid_stairs")
    reason: str = ""                            # "계단 회피 조건 위반: 오행산 정상 계단"
    alternatives: list[Fix] = []                # blocked일 때 대신 제시한 대안
    applied_version: Optional[int] = None       # 적용 후 Trip version


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
    changes: list[ChangeRequest] = []           # [v1.1] 변경 요청 기록 (blocked 포함)
