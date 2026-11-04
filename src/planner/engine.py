"""규칙 기반 일정 엔진: 권역 묶기 → 모드·난이도 조정 → 하루 시간표 → 식당 배치.

우선순위: 영업시간·휴무 → 보행 한도 → 필수 경험(선택한 관광지) → 난이도 상한 → 식사 취향 → 이동 최소화.
"""

import itertools
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from src.planner.geo import travel_leg, travel_minutes
from src.planner.hours import earliest_start, has_weekday_closure, hhmm_to_min, intervals_for, min_to_hhmm
from src.planner.meals import choose_restaurant, is_korean, pinned_restaurant, use_pinned_restaurant
from src.planner.profile_merge import MergedProfile, merge_profiles
from src.planner.schema import (DayPlan, Itinerary, PackageScore, PlanRequest, PlanState, Stop, Unscheduled)
from src.planner.sources import Place, Restaurants, load_places, load_restaurants, load_settings
from src.scoring.package_difficulty import calculate_package
from src.scoring.visit_modes import load_modes

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
MAX_PERMUTATION_PLACES = 6


@dataclass
class Ctx:
    settings: dict
    places: dict[str, Place]
    rest: Restaurants
    profile: MergedProfile
    state: PlanState
    base: tuple[float, float]
    base_is_default: bool
    w_start: int
    w_end: int
    start_weekday: int | None
    catalog: dict
    weights: dict
    assumptions: list[str] = field(default_factory=list)
    korean_meals: set | None = None   # 하루 구성(compose)이 한식으로 정한 (day_idx, 'lunch'|'dinner'). None이면 기존 규칙

    def weekday(self, day_idx: int) -> int | None:
        return None if self.start_weekday is None else (self.start_weekday + day_idx) % 7

    def travel(self, a, b) -> int:
        """택시 기준 이동 분(용량 추정·순서 비교용)."""
        return travel_minutes(a, b, self.settings["travel"])

    def leg(self, a, b) -> tuple[int, str]:
        """(분, 'walk'|'taxi'). 보행 속도·연속 보행 한도를 반영한 실제 이동."""
        return travel_leg(a, b, self.profile.speed_mps, self.settings["travel"], self.profile.walk_limit_min)

    def note(self, text: str) -> None:
        if text not in self.assumptions:
            self.assumptions.append(text)


def walk_minutes(place: Place, mode: str, ctx: Ctx) -> int:
    score = place.modes[mode]["dimensions"]["walking"]["score"]
    base = ctx.settings["walk"]["score_to_walk_min"][str(score)]
    scale = ctx.settings["walk"]["reference_speed_mps"] / ctx.profile.speed_mps
    return max(1, round(base * scale))


def _mode_score(place: Place, mode: str) -> int:
    return place.modes[mode]["score"]


# ---------------------------------------------------------------- 1. 날짜 배정

def _usable_minutes(ctx: Ctx) -> float:
    meal = ctx.settings["meal"]
    base = (ctx.w_end - ctx.w_start) - 2 * (meal["duration_min"] + 2 * meal["travel_allowance_min"])
    return base * ctx.settings["pace"][ctx.state.pace]["capacity_factor"]


def _load(place: Place, ctx: Ctx) -> int:
    return place.stay_min + ctx.settings["capacity"]["per_place_travel_min"]


def _cluster_capacity(places: list[Place], ctx: Ctx) -> float:
    overhead = max(2 * ctx.travel(ctx.base, p.coord) for p in places) if places else 0
    return max(120.0, _usable_minutes(ctx) - overhead)


def assign_days(place_ids: list[str], n_days: int, ctx: Ctx) -> tuple[dict[int, list[str]], list[Unscheduled]]:
    """여유 있게 분산해 보고, 못 넣는 곳이 생기면 하루를 꽉 채워서 다시 배정한다."""
    spread = ctx.settings["capacity"]["spread_ratio"]
    result, unscheduled = _assign(place_ids, n_days, ctx, spread)
    if unscheduled and spread < 1.0:
        result, unscheduled = _assign(place_ids, n_days, ctx, 1.0)
    return result, unscheduled


def _assign(place_ids: list[str], n_days: int, ctx: Ctx, spread: float) -> tuple[dict[int, list[str]], list[Unscheduled]]:
    """권역이 다른 관광지는 같은 날 섞지 않는다. 저녁에야 여는 곳은 같은 권역 낮 일정과 묶는다."""
    S = ctx.settings
    order = S["clusters"]["order"]
    days: dict[int, dict] = {d: {"pids": [], "cluster": None, "load": 0.0} for d in range(1, n_days + 1)}
    unscheduled: list[Unscheduled] = []

    pinned = {p: d for p, d in ctx.state.pins.items() if p in place_ids and 1 <= d <= n_days}
    for pid, d in pinned.items():
        place = ctx.places[pid]
        days[d]["pids"].append(pid)
        days[d]["cluster"] = days[d]["cluster"] or place.cluster
        days[d]["load"] += _load(place, ctx)

    by_cluster: dict[str, list[Place]] = defaultdict(list)
    for pid in place_ids:
        if pid not in pinned:
            by_cluster[ctx.places[pid].cluster].append(ctx.places[pid])

    bins: list[dict] = []
    for cluster, plist in by_cluster.items():
        cap = _cluster_capacity(plist, ctx) * spread
        current: list[dict] = []
        for p in sorted(plist, key=lambda x: (x.evening, -_load(x, ctx))):
            if p.evening and not p.solo:
                full = _cluster_capacity(plist, ctx)
                target = next((b for b in current if b["load"] + _load(p, ctx) <= full), None)
                if target is None:
                    target = {"cluster": cluster, "pids": [], "load": 0.0, "solo": False}
                    current.append(target)
                target["pids"].append(p.id)
                target["load"] += _load(p, ctx)
                continue
            if p.solo:
                bins.append({"cluster": cluster, "pids": [p.id], "load": _load(p, ctx), "solo": True})
                continue
            target = next((b for b in current if b["load"] + _load(p, ctx) <= cap), None)
            if target is None:
                target = {"cluster": cluster, "pids": [], "load": 0.0, "solo": False}
                current.append(target)
            target["pids"].append(p.id)
            target["load"] += _load(p, ctx)
        bins.extend(current)
    bins.sort(key=lambda b: (order.index(b["cluster"]) if b["cluster"] in order else 99, -b["load"]))

    def fits(day: dict, b: dict, ratio: float) -> bool:
        if day["cluster"] is None:
            return True
        if b["solo"] or day["cluster"] != b["cluster"]:
            return False
        members = [ctx.places[p] for p in day["pids"]]
        return day["load"] + b["load"] <= _cluster_capacity(members, ctx) * ratio

    def place_bin(b: dict, ratio: float) -> bool:
        candidates = [d for d in days if fits(days[d], b, ratio)]
        if not candidates:
            return False
        empty = [d for d in candidates if days[d]["cluster"] is None]
        d = empty[0] if empty else max(candidates, key=lambda x: -days[x]["load"])
        days[d]["pids"].extend(b["pids"])
        days[d]["cluster"] = days[d]["cluster"] or b["cluster"]
        days[d]["load"] += b["load"]
        return True

    leftovers = [b for b in bins if not place_bin(b, spread)]
    singles = [b for b in leftovers if not place_bin(b, 1.0)]
    for b in singles:
        for pid in b["pids"]:
            single = {"cluster": b["cluster"], "pids": [pid], "load": _load(ctx.places[pid], ctx), "solo": ctx.places[pid].solo}
            if not place_bin(single, 1.0):
                unscheduled.append(Unscheduled(place_id=pid, reason="일수가 부족하거나 권역이 달라 같은 날 배치할 수 없습니다."))

    _spread_to_empty_days(days, set(pinned), ctx)
    return {d: v["pids"] for d, v in days.items()}, unscheduled


def _spread_to_empty_days(days: dict[int, dict], pinned: set[str], ctx: Ctx) -> None:
    """빈 날이 남으면 가장 빽빽한 날에서 가장 힘든 곳을 옮겨 하루 부담을 줄인다."""
    while True:
        empty = [d for d, v in days.items() if not v["pids"]]
        movable = [(d, [p for p in v["pids"] if p not in pinned]) for d, v in days.items() if len(v["pids"]) >= 2]
        movable = [(d, ps) for d, ps in movable if ps]
        if not empty or not movable:
            return
        d_src, candidates = max(movable, key=lambda x: len(x[1]))
        day_pids = days[d_src]["pids"]
        candidates = [p for p in candidates if not ctx.places[p].evening
                      and any(q != p and not ctx.places[q].evening for q in day_pids)]
        if not candidates:
            return
        pid = max(candidates, key=lambda p: _mode_score(ctx.places[p], "standard"))
        d_dst = empty[0]
        days[d_src]["pids"].remove(pid)
        days[d_dst]["pids"].append(pid)
        days[d_dst]["cluster"] = ctx.places[pid].cluster


# ---------------------------------------------------------------- 2. 관람 방식·난이도

def _day_difficulty(pids: list[str], modes: dict[str, str], ctx: Ctx) -> int:
    days = [[{"place_id": p, "mode": modes[p]} for p in pids]]
    return calculate_package(days, ctx.catalog)["days"][0]["difficulty"]


def select_modes(pids: list[str], ctx: Ctx) -> dict[str, str]:
    low = ctx.settings["walk"]["low_stamina"]
    stamina_low = ctx.profile.walk_limit_min <= low["limit_min_at_most"] or ctx.profile.speed_mps < low["speed_mps_below"]
    modes: dict[str, str] = {}
    for pid in pids:
        place = ctx.places[pid]
        override = ctx.state.mode_overrides.get(pid)
        if override:
            modes[pid] = override
            continue
        walking = place.modes["standard"]["dimensions"]["walking"]["score"]
        if stamina_low and walking >= low["auto_short_walking_score_at_least"]:
            modes[pid] = "short"
            ctx.note(f"보행 한도가 짧아 {place.name}은(는) '{place.modes['short']['name']}' 코스로 잡았습니다.")
        else:
            modes[pid] = "standard"

    limit = ctx.settings["difficulty"]["max_day_difficulty"]
    while pids and _day_difficulty(pids, modes, ctx) > limit:
        adjustable = [p for p in pids if p not in ctx.state.mode_overrides and modes[p] != "short"]
        if not adjustable:
            ctx.note(f"하루 난이도가 상한({limit})을 넘지만 사용자가 고른 방식이라 조정하지 않았습니다.")
            break
        worst = max(adjustable, key=lambda p: _mode_score(ctx.places[p], modes[p]))
        modes[worst] = "short"
        worst_place = ctx.places[worst]
        ctx.note(f"하루 난이도를 낮추기 위해 {worst_place.name}은(는) '{worst_place.modes['short']['name']}' 코스로 바꿨습니다.")
    return modes


# ---------------------------------------------------------------- 3. 하루 시간표

@dataclass
class SimResult:
    stops: list[Stop]
    anchors: list[dict | None]
    cost: float
    violations: dict[str, str]
    walk_total: int
    max_cont: int
    placements: list[tuple[str, str]]


def _hhmm(m: int) -> str:
    return min_to_hhmm(m)


def simulate(order: list[str], modes: dict[str, str], day_idx: int, ctx: Ctx) -> SimResult:
    S = ctx.settings
    meal = S["meal"]
    dur = meal["duration_min"]
    allow = meal["travel_allowance_min"]
    lunch_e, lunch_l = hhmm_to_min(meal["lunch_earliest"]), hhmm_to_min(meal["lunch_latest_start"])
    dinner_e, dinner_l = hhmm_to_min(meal["dinner_earliest"]), hhmm_to_min(meal["dinner_latest_start"])
    dinner_after = hhmm_to_min(meal["dinner_if_activity_ends_after"])
    limit, rest_min = ctx.profile.walk_limit_min, S["walk"]["rest_min"]
    wd = ctx.weekday(day_idx)
    W = ctx.weights

    st = {"t": ctx.w_start, "loc": ctx.base, "loc_id": None, "cont": 0, "max_cont": 0,
          "lunch": False, "dinner": False, "pending": 0, "act_end": 0}
    lunch_split_end = hhmm_to_min(meal["lunch_split_if_ends_after"])
    stops: list[Stop] = []
    anchors: list[dict | None] = []
    violations: dict[str, str] = {}
    totals = {"travel": 0, "wait": 0, "walk": 0, "pen": 0.0}
    placements: list[tuple[str, str]] = []

    def push(stop: Stop, anchor: dict | None = None) -> None:
        stops.append(stop)
        anchors.append(anchor)

    def add_meal(kind: str, at: int, loc, loc_id, in_site: str | None = None) -> None:
        start = max(st["t"], at)
        span = dur + (0 if in_site else 2 * allow)
        push(Stop(type="meal", meal=kind, start=_hhmm(start), end=_hhmm(start + span)),
             {"kind": kind, "start": start, "end": start + span, "eat": dur, "loc": loc, "loc_id": loc_id,
              "in_site": in_site})
        st["t"], st["cont"], st["pending"] = start + span, 0, 0
        st[kind] = True
        if kind == "dinner" and start > dinner_l:
            totals["pen"] += W["late_end"] * (start - dinner_l)

    def walk_leg(minutes: int) -> None:
        total = st["cont"] + minutes
        rests = max(0, math.ceil(total / limit) - 1)
        st["max_cont"] = max(st["max_cont"], min(total, limit))
        st["pending"] += rests
        st["cont"] = total - rests * limit
        totals["walk"] += minutes

    def add_move(dest, note: str) -> int:
        minutes, how = ctx.leg(st["loc"], dest)
        if minutes:
            push(Stop(type="move", start=_hhmm(st["t"]), end=_hhmm(st["t"] + minutes), minutes=minutes,
                      transport=how, note=note))
            st["t"] += minutes
            totals["travel"] += minutes
            if how == "walk":
                walk_leg(minutes)
        return minutes

    def flush_rests() -> None:
        for _ in range(st["pending"]):
            push(Stop(type="rest", start=_hhmm(st["t"]), end=_hhmm(st["t"] + rest_min), minutes=rest_min,
                      reason="연속 보행 한도를 넘지 않도록 앉아서 쉽니다."))
            st["t"] += rest_min
        st["pending"] = 0

    def segment(place: Place, mode: str, start: int, stay: int, w: int, label: str | None) -> None:
        """관광지 구간 하나. 연속 보행이 한도를 넘으면 구간 뒤에 휴식을 넣는다."""
        total = st["cont"] + w
        rests = max(0, math.ceil(total / limit) - 1)
        st["max_cont"] = max(st["max_cont"], min(total, limit))
        push(Stop(type="attraction", place_id=place.id, name=place.name, mode=mode,
                  mode_name=place.modes[mode]["name"], start=_hhmm(start), end=_hhmm(start + stay),
                  walk_min=w, note=label))
        st["t"] = st["act_end"] = start + stay
        st["pending"] += rests
        st["cont"] = total - rests * limit
        totals["walk"] += w

    base_name = ctx.settings["base_point"]["name"] if ctx.base_is_default else "출발지"
    if order:
        push(Stop(type="base", start=_hhmm(st["t"]), end=_hhmm(st["t"]), note=f"출발: {base_name}"))

    prev_demanding = False
    for pid in order:
        place, mode = ctx.places[pid], modes[pid]
        if not st["lunch"] and st["t"] >= lunch_e:
            add_meal("lunch", st["t"], st["loc"], st["loc_id"])
        if not st["dinner"] and st["t"] >= dinner_e:
            add_meal("dinner", st["t"], st["loc"], st["loc_id"])

        flush_rests()
        add_move(place.coord, f"→ {place.name}")

        intervals = intervals_for(place.hours, wd)
        stay = place.stay_min
        w = walk_minutes(place, mode, ctx)
        start = earliest_start(intervals, st["t"], stay)
        if start is None:
            violations[pid] = "영업시간과 맞지 않거나 휴무일입니다."
            start = st["t"]

        if start > st["t"] and not st["lunch"]:
            lunch_at = max(st["t"], lunch_e)
            if lunch_at <= lunch_l and lunch_at + dur <= start:
                add_meal("lunch", lunch_at, place.coord, pid)
                start = earliest_start(intervals, st["t"], stay)
                if start is None:
                    violations[pid] = "영업시간과 맞지 않거나 휴무일입니다."
                    start = st["t"]

        split = False
        if not st["lunch"] and stay >= 120 and start + stay > lunch_split_end and start <= lunch_e + 60:
            cand = earliest_start(intervals, st["t"], stay + dur)
            if cand is not None:
                start = cand
                lunch_start = max(start + 30, lunch_e)
                part1 = lunch_start - start
                if stay - part1 >= 20:
                    split = True
        totals["wait"] += max(0, start - st["t"])
        st["t"] = start

        if start + stay > ctx.w_end + (dur if split else 0):
            violations.setdefault(pid, "하루 활동 시간을 넘깁니다.")

        if split:
            w1 = round(w * part1 / stay)
            segment(place, mode, start, part1, w1, "식사 전")
            in_site = pid if pid in S["in_site_meal_places"] else None
            add_meal("lunch", lunch_start, place.coord, pid, in_site)
            segment(place, mode, st["t"], stay - part1, w - w1, "식사 후")
        else:
            segment(place, mode, start, stay, w, None)

        demanding = _mode_score(place, mode) >= 6
        if demanding and prev_demanding:
            totals["pen"] += W["consecutive_demanding"]
        prev_demanding = demanding
        st["loc"], st["loc_id"] = place.coord, pid
        placements.append((pid, mode))

    if order:
        if not st["lunch"]:
            add_meal("lunch", lunch_e, st["loc"], st["loc_id"])
        if not st["dinner"]:  # 하루 두 끼: 저녁은 항상 넣는다
            last = ctx.places[st["loc_id"]]
            if last.cluster in ("west", "banahills"):
                add_move(ctx.base, "→ 다낭 시내")
                st["loc"], st["loc_id"] = ctx.base, None
                add_meal("dinner", dinner_e, st["loc"], None)
            else:
                add_meal("dinner", dinner_e, st["loc"], st["loc_id"])
                add_move(ctx.base, "→ 다낭 시내")
        elif st["loc_id"] is not None:
            add_move(ctx.base, "→ 다낭 시내")
        push(Stop(type="base", start=_hhmm(st["t"]), end=_hhmm(st["t"]), note=f"복귀: {base_name}"))

    cost = (W["travel"] * totals["travel"] + W["wait"] * totals["wait"] + totals["pen"]
            + 1000 * len(violations))
    return SimResult(stops, anchors, cost, violations, totals["walk"], st["max_cont"], placements)


def _nearest_neighbor(pids: list[str], ctx: Ctx) -> list[str]:
    remaining, order, loc = list(pids), [], ctx.base
    while remaining:
        nxt = min(remaining, key=lambda p: ctx.travel(loc, ctx.places[p].coord))
        order.append(nxt)
        loc = ctx.places[nxt].coord
        remaining.remove(nxt)
    return order


def schedule_day(day_idx: int, pids: list[str], modes: dict[str, str], ctx: Ctx) -> tuple[SimResult, list[Unscheduled]]:
    remaining, dropped = list(pids), []
    while True:
        if not remaining:
            return simulate([], modes, day_idx, ctx), dropped
        candidates = (itertools.permutations(remaining) if len(remaining) <= MAX_PERMUTATION_PLACES
                      else [_nearest_neighbor(remaining, ctx)])
        best = min((simulate(list(o), modes, day_idx, ctx) for o in candidates),
                   key=lambda r: (len(r.violations), r.cost))
        if not best.violations:
            return best, dropped
        for pid, reason in best.violations.items():
            remaining.remove(pid)
            dropped.append(Unscheduled(place_id=pid, reason=reason))


# ---------------------------------------------------------------- 4. 식당 배치

def _needs_korean(ctx: Ctx, day_idx: int) -> bool:
    interval = ctx.settings["korean_interval_days"].get(ctx.profile.korean_need)
    return interval is not None and day_idx % interval == 0


def fill_restaurants(day_idx: int, sim: SimResult, ctx: Ctx, used: set[str]) -> None:
    allow = ctx.settings["meal"]["travel_allowance_min"]
    metas = [(i, a) for i, a in enumerate(sim.anchors) if a]
    korean_slot = None
    if ctx.korean_meals is None and _needs_korean(ctx, day_idx) and metas:
        flexible = [(i, a) for i, a in metas if not a["in_site"]]
        dinners = [i for i, a in flexible if a["kind"] == "dinner"]
        if dinners or flexible:
            korean_slot = dinners[0] if dinners else flexible[0][0]
        else:
            ctx.note(f"{day_idx + 1}일차는 식사가 모두 고정(바나힐 뷔페)이라 한식을 넣지 못했습니다.")
    wd = ctx.weekday(day_idx)
    excluded = set(ctx.state.excluded_restaurants)
    reserved = set(ctx.state.meal_pins.values())

    picks: dict[int, tuple] = {}
    for i, a in metas:
        stop = sim.stops[i]
        if not ctx.rest.available:
            ctx.note("식당 데이터 파일이 없어 식사 장소를 배치하지 못했습니다.")
            continue
        if a["in_site"]:
            pick = pinned_restaurant(ctx.rest, a["in_site"])
            if pick:
                used.add(pick.place_id)
                picks[i] = (pick, True)
                continue
        want_korean = (day_idx, a["kind"]) in ctx.korean_meals if ctx.korean_meals is not None else i == korean_slot
        eat_start, eat_end = a["start"], a["start"] + a["eat"]
        pinned_id = ctx.state.meal_pins.get(f"{day_idx + 1}:{a['kind']}")
        pick = None
        if pinned_id and pinned_id not in used and pinned_id not in excluded:
            pick = use_pinned_restaurant(ctx.rest, pinned_id, a["loc"], eat_start, eat_end, wd, ctx.leg, allow,
                                         ctx.profile)
            if pick and want_korean and not pick.is_korean:
                pick = None
        if pick is None:
            args = (ctx.rest, a["loc"], eat_start, eat_end, wd, ctx.profile, ctx.settings, used | excluded | reserved)
            pick = choose_restaurant(*args, want_korean, ctx.leg, allow)
            if pick is None and want_korean:
                ctx.note(f"{day_idx + 1}일차에 조건에 맞는 한식당을 찾지 못해 일반 식당으로 대체했습니다.")
                pick = choose_restaurant(*args, False, ctx.leg, allow)
        if pick is None:
            stop.note = "조건에 맞는 식당 후보를 찾지 못했습니다."
            continue
        used.add(pick.place_id)
        if pick.hours_unknown:
            ctx.note(f"{pick.name}은(는) 영업시간 정보가 없어 영업 여부를 확인하지 못했습니다.")
        picks[i] = (pick, False)

    for i in sorted((i for i, _ in metas), reverse=True):
        a, stop = sim.anchors[i], sim.stops[i]
        chosen = picks.get(i)
        if chosen is None:
            stop.end = _hhmm(a["start"] + a["eat"])
            continue
        pick, fixed = chosen
        t = a["start"]
        out: list[Stop] = []
        if pick.travel_min:
            out.append(Stop(type="move", start=_hhmm(t), end=_hhmm(t + pick.travel_min), minutes=pick.travel_min,
                            transport=pick.transport, note=f"→ {pick.name}"))
            t += pick.travel_min
        stop.start, stop.end = _hhmm(t), _hhmm(t + a["eat"])
        stop.restaurant, stop.fixed = pick, fixed
        out.append(stop)
        t += a["eat"]
        if pick.travel_min:
            out.append(Stop(type="move", start=_hhmm(t), end=_hhmm(t + pick.travel_min), minutes=pick.travel_min,
                            transport=pick.transport, note="→ 다음 장소"))
        sim.stops[i:i + 1] = out


# ---------------------------------------------------------------- 5. 전체 조립

def _build_ctx(request: PlanRequest, rest: Restaurants | None) -> Ctx:
    settings = load_settings()
    places = load_places()
    unknown = [p for p in request.place_ids if p not in places]
    if unknown:
        raise ValueError(f"알 수 없는 관광지: {', '.join(unknown)}")
    window = request.day_window
    w_start = hhmm_to_min(window.start if window else settings["day_window"]["start"])
    w_end = hhmm_to_min(window.end if window else settings["day_window"]["end"])
    base = request.start_point or None
    base_xy = (base.lat, base.lng) if base else (settings["base_point"]["lat"], settings["base_point"]["lng"])
    profile = merge_profiles(request.travelers, request.state, settings)
    weights = {**settings["weights"], **request.state.weights}
    ctx = Ctx(settings, places, rest if rest is not None else load_restaurants(), profile, request.state,
              base_xy, base is None, w_start, w_end, request.start_date.weekday() if request.start_date else None,
              load_modes(), weights)
    for n in profile.notes:
        ctx.note(n)
    return ctx


def _food_assumptions(ctx: Ctx) -> None:
    """프로필의 음식 조건 중 식당 데이터로 확인할 수 없는 것을 안내한다."""
    if not ctx.rest.available:
        return
    profile, restaurants = ctx.profile, ctx.rest.by_id.values()
    tagged = any("ingredient_tags" in r for r in restaurants)
    has_venue = any(r.get("venue_type") in ("restaurant", "street_food") for r in restaurants)
    if profile.avoid_ingredients and not tagged:
        ctx.note(f"피하는 재료({', '.join(sorted(profile.avoid_ingredients))})는 식당 재료 태그가 없어 "
                 "식당 종류로만 걸렀습니다. 주문 시 확인이 필요합니다.")
    elif profile.avoid_ingredients:
        ctx.note("재료 태그는 리뷰에서 확인된 재료만 담겨 있어, 태그가 없다고 해당 재료가 없다는 뜻은 아닙니다. "
                 "주문 시 확인이 필요합니다.")
    if profile.venues != {"restaurant", "street_food"} and not has_venue:
        ctx.note("식사 장소 유형 정보가 식당 데이터에 없어 장소 선호는 반영하지 못했습니다.")
    if profile.avoid_other:
        ctx.note(f"직접 입력한 기피 재료({', '.join(profile.avoid_other)})는 아직 식당 선택에 반영하지 못했습니다.")


def _collect_assumptions(request: PlanRequest, ctx: Ctx) -> None:
    _food_assumptions(ctx)
    ctx.note("체류 시간은 일반 관광 소요시간 기준 추정(brief 60분·half 120분·long 240분)이며 실제와 다를 수 있습니다.")
    ctx.note("이동시간은 직선거리 기반 추정(도로 보정 1.3, 평균 35km/h)이며 실제 교통과 다를 수 있습니다.")
    for pid in request.place_ids:
        place = ctx.places[pid]
        if place.hours_source == "manual" and place.hours_confidence != "high":
            ctx.note(f"{place.name}의 영업시간은 확인되지 않아 가정값을 사용했습니다(신뢰도 {place.hours_confidence}).")
        elif place.hours_source == "unknown":
            ctx.note(f"{place.name}의 영업시간 정보가 없어 상시 개방으로 가정했습니다.")
        if request.start_date is None and has_weekday_closure(place.hours):
            ctx.note(f"출발일이 없어 {place.name}의 요일별 휴무를 반영하지 못했습니다.")
        if place.status != "ok":
            ctx.note(f"{place.name}의 난이도 점수는 검수 대기 상태입니다.")


def _reseat_dropped(assignment: dict[int, list[str]], sims: dict[int, SimResult], modes_by_day: dict[int, dict],
                    dropped: list[Unscheduled], ctx: Ctx) -> list[Unscheduled]:
    """휴무·마감으로 빠진 관광지를 같은 권역이 가능한 다른 날로 옮겨 본다(사용자가 고정한 곳은 제외)."""
    remaining: list[Unscheduled] = []
    for u in dropped:
        place = ctx.places[u.place_id]
        seated = False
        if u.place_id not in ctx.state.pins:
            for day in sorted(assignment, key=lambda d: len(assignment[d])):
                members = [ctx.places[p] for p in assignment[day]]
                if members and (place.solo or any(m.solo for m in members) or members[0].cluster != place.cluster):
                    continue
                pids = assignment[day] + [u.place_id]
                modes = select_modes(pids, ctx)
                sim, lost = schedule_day(day - 1, pids, modes, ctx)
                if not lost and u.place_id in dict(sim.placements):
                    assignment[day], sims[day], modes_by_day[day] = pids, sim, modes
                    seated = True
                    break
        if not seated:
            remaining.append(u)
    return remaining


def build_itinerary(request: PlanRequest, rest: Restaurants | None = None) -> Itinerary:
    ctx = _build_ctx(request, rest)
    _collect_assumptions(request, ctx)
    place_ids = list(dict.fromkeys(request.place_ids))
    n_days = request.days

    comp = None
    try:  # 피로 예산 기반 하루 구성. 다루지 못하는 입력은 기존 상자 방식으로 넘긴다
        from src.planner.compose import ComposeUnsupported, compose_days
        comp = compose_days(ctx, place_ids, n_days, select_modes)
    except ComposeUnsupported:
        comp = None
    if comp is not None:
        assignment, unscheduled = comp.assignment, comp.unscheduled
        ctx.state = ctx.state.model_copy(update={"meal_pins": {**comp.meal_pins, **ctx.state.meal_pins}})
        ctx.korean_meals = set()   # 이미 고정된 식당이 있는 끼니는 그 식당의 한식 여부를 따른다(고정한 날을 바꾸지 않음)
        for d, plan in comp.plans.items():
            for kind, meal in (("lunch", plan.lunch), ("dinner", plan.dinner)):
                pin = ctx.state.meal_pins.get(f"{d}:{kind}")
                ko = is_korean(ctx.rest.by_id[pin]) if pin and pin in ctx.rest.by_id else bool(meal and meal["ko"])
                if ko:
                    ctx.korean_meals.add((d - 1, kind))
        for note in comp.notes:
            ctx.note(note)
    else:
        assignment, unscheduled = assign_days(place_ids, n_days, ctx)
    sims: dict[int, SimResult] = {}
    modes_by_day: dict[int, dict] = {}
    dropped: list[Unscheduled] = []
    for day in range(1, n_days + 1):
        pids = assignment[day]
        planned = comp.modes.get(day) if comp is not None else None
        modes_by_day[day] = planned if planned and set(planned) == set(pids) else (select_modes(pids, ctx) if pids else {})
        sims[day], lost = schedule_day(day - 1, pids, modes_by_day[day], ctx)
        dropped.extend(lost)
        assignment[day] = [p for p, _ in sims[day].placements] or []
    unscheduled.extend(_reseat_dropped(assignment, sims, modes_by_day, dropped, ctx))

    used: set[str] = set()
    plans: list[DayPlan] = []
    new_pins: dict[str, int] = {}
    new_meal_pins: dict[str, str] = {}
    package_days: list[list[dict]] = []
    for day in range(1, n_days + 1):
        sim = sims[day]
        fill_restaurants(day - 1, sim, ctx, used)
        for s in sim.stops:
            if s.type == "meal" and s.restaurant and not s.fixed:
                new_meal_pins[f"{day}:{s.meal}"] = s.restaurant.place_id
        wd = ctx.weekday(day - 1)
        difficulty = None
        if sim.placements:
            package_days.append([{"place_id": p, "mode": m} for p, m in sim.placements])
            difficulty = calculate_package([package_days[-1]], ctx.catalog)["days"][0]["difficulty"]
            for p, _ in sim.placements:
                new_pins[p] = day
        else:
            ctx.note(f"{day}일차는 배치된 관광지가 없어 비어 있습니다.")
        plans.append(DayPlan(day=day, weekday=WEEKDAY_KO[wd] if wd is not None else None, stops=sim.stops,
                             difficulty=difficulty, total_walk_min=sim.walk_total,
                             max_continuous_walk_min=sim.max_cont))

    package = None
    if package_days:
        result = calculate_package(package_days, ctx.catalog)
        package = PackageScore(peak=result["peak"], mean=result["mean"])
    for u in unscheduled:
        ctx.note(f"{ctx.places[u.place_id].name}은(는) 일정에 넣지 못했습니다: {u.reason}")

    state = request.state.model_copy(update={"pins": new_pins, "meal_pins": new_meal_pins})
    stored = request.model_copy(update={"state": state})
    return Itinerary(plan_id=uuid.uuid4().hex[:8], request=stored, days=plans, package=package,
                     unscheduled=unscheduled, assumptions=ctx.assumptions, state=state)
