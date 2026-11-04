"""피드백 명령(EditCommand) 적용과 일정 재생성.

명령은 요청의 state(pins, mode_overrides 등)만 바꾸고, 일정은 같은 엔진이 다시 짠다.
고르지 않은 날은 현재 배치를 pins로 고정해서 그대로 유지한다. 하나라도 잘못된 명령이면
아무것도 적용하지 않고 되묻는다(일정은 바뀌지 않는다).
"""

from src.planner.engine import build_itinerary
from src.planner.profile_merge import merge_profiles, upgrade_korean_need
from src.planner.schema import (AddPlace, AdjustWalkLimit, EditCommand, Itinerary, LightenDay, MoreKoreanMeals,
                                MovePlace, PlanRequest, RefineResponse, RemovePlace, SetMode, SetPace,
                                SwapRestaurant)
from src.planner.sources import Restaurants, load_places, load_settings

MEAL_LABEL = {"lunch": "점심", "dinner": "저녁"}
NO_LLM_MESSAGE = "자연어 피드백 해석은 아직 연결되지 않았습니다. 수정 명령(commands)으로 보내주세요."


def _apply(req: PlanRequest, current: Itinerary, cmd: EditCommand, names: dict[str, str]) -> tuple[str | None, str | None]:
    """(요약, 문제). 문제가 있으면 요약은 None."""
    state = req.state
    places = load_places()

    def day_ok(day: int) -> bool:
        return 1 <= day <= req.days

    if isinstance(cmd, LightenDay):
        if not day_ok(cmd.day):
            return None, f"{cmd.day}일차는 여행 일수({req.days}일) 밖입니다."
        pids = [p for p, d in state.pins.items() if d == cmd.day]
        if not pids:
            return None, f"{cmd.day}일차에는 조정할 관광지가 없습니다."
        for pid in pids:
            state.mode_overrides[pid] = "short"
        changes = ", ".join(f"{names[p]}('{places[p].modes['short']['name']}')" for p in pids)
        return f"{cmd.day}일차를 가볍게: {changes} 코스로 변경", None

    if isinstance(cmd, AddPlace):
        if cmd.place_id not in places:
            return None, f"알 수 없는 관광지입니다: {cmd.place_id}"
        if cmd.place_id in req.place_ids:
            return None, f"{places[cmd.place_id].name}은(는) 이미 일정에 있습니다."
        if cmd.day is not None and not day_ok(cmd.day):
            return None, f"{cmd.day}일차는 여행 일수({req.days}일) 밖입니다."
        req.place_ids.append(cmd.place_id)
        if cmd.day is not None:
            state.pins[cmd.place_id] = cmd.day
        names[cmd.place_id] = places[cmd.place_id].name
        where = f" ({cmd.day}일차)" if cmd.day else ""
        return f"{places[cmd.place_id].name} 추가{where}", None

    if isinstance(cmd, RemovePlace):
        if cmd.place_id not in req.place_ids:
            return None, f"일정에 없는 관광지입니다: {cmd.place_id}"
        req.place_ids.remove(cmd.place_id)
        state.pins.pop(cmd.place_id, None)
        state.mode_overrides.pop(cmd.place_id, None)
        return f"{names[cmd.place_id]} 제외", None

    if isinstance(cmd, MovePlace):
        if cmd.place_id not in req.place_ids:
            return None, f"일정에 없는 관광지입니다: {cmd.place_id}"
        if not day_ok(cmd.day):
            return None, f"{cmd.day}일차는 여행 일수({req.days}일) 밖입니다."
        state.pins[cmd.place_id] = cmd.day
        return f"{names[cmd.place_id]}을(를) {cmd.day}일차로 이동", None

    if isinstance(cmd, SetMode):
        if cmd.place_id not in req.place_ids:
            return None, f"일정에 없는 관광지입니다: {cmd.place_id}"
        state.mode_overrides[cmd.place_id] = cmd.mode
        return f"{names[cmd.place_id]} 관람 방식을 {places[cmd.place_id].modes[cmd.mode]['name']}(으)로 변경", None

    if isinstance(cmd, MoreKoreanMeals):
        profile = merge_profiles(req.travelers, state, load_settings())
        state.korean_need_override = upgrade_korean_need(profile.korean_need)
        return f"한식 빈도를 '{profile.korean_need}' → '{state.korean_need_override}'로 상향", None

    if isinstance(cmd, SwapRestaurant):
        if not day_ok(cmd.day):
            return None, f"{cmd.day}일차는 여행 일수({req.days}일) 밖입니다."
        key = f"{cmd.day}:{cmd.meal}"
        old_id = state.meal_pins.get(key)
        if not old_id:
            return None, f"{cmd.day}일차 {MEAL_LABEL[cmd.meal]}에는 바꿀 식당이 없습니다(고정된 식사이거나 식당이 배치되지 않았습니다)."
        old_name = _meal_names(current).get((cmd.day, cmd.meal), old_id)
        state.excluded_restaurants.append(old_id)
        state.meal_pins.pop(key)
        return f"{cmd.day}일차 {MEAL_LABEL[cmd.meal]} 식당 교체: {old_name} 제외", None

    if isinstance(cmd, AdjustWalkLimit):
        settings = load_settings()
        current_limit = merge_profiles(req.travelers, state, settings).base_limit_min
        steps = sorted(set(settings["walk"]["limits_by_duration"].values()))
        if cmd.direction == "more":
            options = [s for s in steps if s > current_limit]
            if not options:
                return None, f"연속 보행 한도가 이미 가장 높은 단계({current_limit}분)입니다."
            new_limit = options[0]
        else:
            options = [s for s in steps if s < current_limit]
            if not options:
                return None, f"연속 보행 한도가 이미 가장 낮은 단계({current_limit}분)입니다."
            new_limit = options[-1]
        state.walk_limit_override = new_limit
        return f"연속 보행 한도 {current_limit}분 → {new_limit}분", None

    if isinstance(cmd, SetPace):
        state.pace = cmd.pace
        label = {"slower": "더 여유 있게", "normal": "기본 속도로", "faster": "더 빠르게"}[cmd.pace]
        return f"전체 속도를 {label} 조정", None

    return None, "지원하지 않는 명령입니다."


def _meal_names(it: Itinerary) -> dict[tuple[int, str], str]:
    return {(d.day, s.meal): s.restaurant.name for d in it.days for s in d.stops
            if s.type == "meal" and s.restaurant}


def _diff_lines(before: Itinerary, after: Itinerary) -> list[str]:
    old = {p: d for p, d in before.state.pins.items()}
    new = {p: d for p, d in after.state.pins.items()}
    names = {p.id: p.name for p in load_places().values()}
    lines: list[str] = []
    for pid in sorted(set(old) | set(new)):
        if pid not in new:
            lines.append(f"{names[pid]}: {old[pid]}일차 → 일정에서 빠짐")
        elif pid not in old:
            lines.append(f"{names[pid]}: 새로 {new[pid]}일차에 배치")
        elif old[pid] != new[pid]:
            lines.append(f"{names[pid]}: {old[pid]}일차 → {new[pid]}일차")
    old_meals, new_meals = _meal_names(before), _meal_names(after)
    for (day, meal), old_name in sorted(old_meals.items()):
        new_name = new_meals.get((day, meal))
        if new_name != old_name:
            lines.append(f"{day}일차 {MEAL_LABEL[meal]}: {old_name} → {new_name or '식당 후보 없음'}")
    if before.package and after.package and before.package.peak != after.package.peak:
        lines.append(f"가장 힘든 날 난이도 {before.package.peak} → {after.package.peak}")
    return lines


def refine(current: Itinerary, commands: list[EditCommand], feedback: str | None = None,
           rest: Restaurants | None = None, interpreter=None) -> RefineResponse:
    """명령이 없고 피드백만 있으면 interpreter(자연어 -> 명령 변환)로 명령을 만든다. 없으면 안내만 돌려준다."""
    notes = ""
    if not commands and feedback and interpreter is not None:
        result = interpreter.interpret(current, feedback)
        commands, notes = result.commands, result.notes()
        if not commands:
            return RefineResponse(itinerary=current, clarification=notes or "적용할 수 있는 수정 명령을 찾지 못했습니다.")
    if not commands:
        message = NO_LLM_MESSAGE if feedback else "적용할 수정 명령이 없습니다."
        return RefineResponse(itinerary=current, clarification=message)

    req = current.request.model_copy(deep=True)
    req.state.pins = dict(current.state.pins)
    req.state.meal_pins = dict(current.state.meal_pins)
    swaps = [(f"{c.day}:{c.meal}", current.state.meal_pins.get(f"{c.day}:{c.meal}"))
             for c in commands if isinstance(c, SwapRestaurant)]
    names = {p.id: p.name for p in load_places().values()}

    summaries: list[str] = []
    problems: list[str] = []
    for cmd in commands:
        summary, problem = _apply(req, current, cmd, names)
        (problems if problem else summaries).append(problem or summary)
    if problems:
        return RefineResponse(itinerary=current, clarification=" ".join(([notes] if notes else []) + problems))

    updated = build_itinerary(req, rest)
    for key, old_id in swaps:
        new_id = updated.state.meal_pins.get(key)
        if old_id and (new_id is None or new_id == old_id):
            day, meal = key.split(":")
            return RefineResponse(itinerary=current, clarification=(
                f"{day}일차 {MEAL_LABEL[meal]}에 대체할 다른 식당 후보를 찾지 못했습니다."))
    summary_text = "\n".join(summaries + _diff_lines(current, updated))
    return RefineResponse(itinerary=updated, applied_commands=commands, change_summary=summary_text,
                          clarification=notes or None)
