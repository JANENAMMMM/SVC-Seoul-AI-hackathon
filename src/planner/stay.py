"""관광지 체류 시간 단계(brief/half/long) 결정.

우선순위: 수동 지정 > Google 유형별 기본값 > fallback. 규칙으로 정한 값에는
걷는 시간 보정을 적용한다. 새 관광지는 유형만 있으면 코드 수정 없이 값이 채워진다.
"""

import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).with_name("stay_config.json")


def load_config(path: Path = _CONFIG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raise_level(level: str, steps: int, order: list[str]) -> str:
    return order[min(order.index(level) + steps, len(order) - 1)]


def level_by_rule(place: dict, config: dict) -> tuple[str, str]:
    """유형별 기본값 → 걷는 시간 보정. (단계, 출처) 반환."""
    types = place.get("types") or []
    order = config["level_order"]
    level, source = config["fallback_level"], "fallback"
    for t in types:
        if t in config["ignored_types"]:
            continue
        if t in config["type_defaults"]:
            level, source = config["type_defaults"][t], f"type:{t}"
            break

    adj = config["walk_adjustment"]
    walk_min = place.get("walk_min")
    if walk_min is not None and walk_min >= adj["walk_min_at_least"]:
        level = _raise_level(level, adj["raise_levels"], order)
        source += "+walk"
    return level, source


def resolve_stay(place: dict, config: dict | None = None) -> tuple[str, str]:
    """(체류 단계, 출처). 수동 지정이 있으면 그대로 쓴다."""
    config = config or load_config()
    manual = place.get("stay_level")
    if manual and place.get("stay_source", "").startswith("manual"):
        return manual, place["stay_source"]
    return level_by_rule(place, config)


def stay_minutes(level: str, config: dict | None = None) -> int:
    config = config or load_config()
    return config["levels"][level]["minutes"]
