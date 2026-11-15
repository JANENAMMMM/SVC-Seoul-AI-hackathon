"""여러 동행자의 프로필을 '가장 약한 사람 기준'으로 하나로 합친다."""

from dataclasses import dataclass, field

from src.planner.schema import PlanState
from src.profile.schema import ParentProfile

_DURATION_ORDER = ["under_15min", "15_30min", "30_60min", "1_2hour", "over_2hour"]
_KOREAN_RANK = ["daily", "every_2_3_days", "occasional", "none", "unknown"]
_KOREAN_UPGRADE = {"unknown": "occasional", "none": "occasional", "occasional": "every_2_3_days",
                   "every_2_3_days": "daily", "daily": "daily"}


@dataclass
class MergedProfile:
    speed_mps: float
    walk_limit_min: int
    base_limit_min: int
    korean_need: str
    local_food: str
    avoid_ingredients: set[str]
    avoid_other: list[str]
    notes: list[str] = field(default_factory=list)
    venues: set[str] = field(default_factory=lambda: {"restaurant", "street_food"})
    fatigue_budget: int = 9  # 하루 관광지 점수 합 상한 (부모님 프로필로 결정)


_ALL_VENUES = {"restaurant", "street_food"}


def _merge_venues(travelers: list[ParentProfile], notes: list[str]) -> set[str]:
    """동행자가 모두 이용할 수 있는 식사 장소. 모름·미선택은 제한 없음, 겹치는 곳이 없으면 제한하지 않는다."""
    allowed = set(_ALL_VENUES)
    for t in travelers:
        mine = set(t.venues)
        if mine and "unknown" not in mine:
            allowed &= mine
    if not allowed:
        notes.append("동행자가 모두 이용할 수 있는 식사 장소가 겹치지 않아 장소 유형은 제한하지 않았습니다.")
        return set(_ALL_VENUES)
    return allowed


def merge_profiles(travelers: list[ParentProfile], state: PlanState, settings: dict) -> MergedProfile:
    walk = settings["walk"]
    notes: list[str] = []

    speeds = [t.walking_speed.base_speed_mps for t in travelers if t.walking_speed]
    if speeds:
        speed = min(speeds)
    else:
        speed = walk["default_speed_mps"]
        notes.append(f"보행속도 정보가 없어 가정값 {speed}m/s를 사용했습니다.")

    durations = [t.walking_duration for t in travelers if t.walking_duration]
    if state.walk_limit_override:
        base = state.walk_limit_override
        notes.append(f"피드백으로 연속 보행 한도를 {base}분으로 조정했습니다.")
    elif durations:
        base = walk["limits_by_duration"][min(durations, key=_DURATION_ORDER.index)]
    else:
        base = walk["default_limit_min"]
        notes.append(f"보행 지속시간 정보가 없어 연속 보행 한도 {base}분을 가정했습니다.")

    pace = settings["pace"][state.pace]
    limit = max(5, round(base * pace["walk_limit_factor"]))

    korean = min((t.korean_need for t in travelers), key=_KOREAN_RANK.index)
    if state.korean_need_override:
        korean = state.korean_need_override
    foods = {t.local_food for t in travelers}
    local = "familiar" if "familiar" in foods else "mixed" if "mixed" in foods else \
        "adventurous" if "adventurous" in foods else "unknown"

    avoid = {i for t in travelers for i in t.avoid_ingredients}
    other = sorted({w for t in travelers for w in t.avoid_other})
    venues = _merge_venues(travelers, notes)
    return MergedProfile(speed, limit, base, korean, local, avoid, other, notes, venues,
                         _fatigue_budget(travelers, state, settings))


def _fatigue_budget(travelers: list[ParentProfile], state: PlanState, settings: dict) -> int:
    """하루 관광지 점수 합 상한. 보행 지속시간으로 기본값을 정하고 나이·걷기 속도로 낮춘다. 여러 명이면 가장 낮은 값."""
    cfg = settings["fatigue"]

    def penalty(t: ParentProfile) -> int:
        p = cfg["age_penalty"] if t.age >= cfg["age_at_or_above"] else 0
        speed = t.walking_speed.base_speed_mps if t.walking_speed else None
        return p + (cfg["speed_penalty"] if speed is not None and speed < cfg["speed_below_mps"] else 0)

    if state.walk_limit_override:  # adjust_walk_limit 명령: 가장 가까운 단계의 예산을 쓴다
        limits = settings["walk"]["limits_by_duration"]
        duration = min(limits, key=lambda k: abs(limits[k] - state.walk_limit_override))
        budget = cfg["budget_by_duration"][duration] - max(penalty(t) for t in travelers)
    else:
        budget = min(cfg["budget_by_duration"][t.walking_duration or cfg["default_duration"]] - penalty(t)
                     for t in travelers)
    budget = max(cfg["min_budget"], budget)
    return max(cfg["min_budget"], round(budget * settings["pace"][state.pace]["capacity_factor"]))


def upgrade_korean_need(current: str) -> str:
    return _KOREAN_UPGRADE[current]
