"""하루 구성 (일정 엔진 1단계): 날짜별로 어떤 관광지와 식당을 묶을지 한 번에 정한다.

기존의 "권역별 상자에 담기"를 대신한다. 관광지를 상자에 담지 않고, 하루 후보(관광지 1~3곳 + 점심·저녁 식당)를
모두 만들어 비용이 낮은 조합을 겹치지 않게 고른다. 이동시간이 간선 가중치이고, 하루가 작아서(최대 3~4곳 + 식사 2번)
모든 순서를 직접 세어 본다.

하드 제약
- 하루 관광지 점수(스코어링 AI)의 합 <= 피로 예산 F (부모님 프로필로 결정). 필요하면 짧은 코스를 쓴다.
- 하루 최대 3곳(필요하면 4곳). 단독 장소(바나힐 등)는 하루를 혼자 쓴다.
- 영업시간, 점심·저녁 시간대, 못 먹는 재료·장소 유형 제외(식당).
- 한식은 여행 전체 조건: 매일이면 매일 한 끼 이상, 2~3일에 한 번이면 ceil(일수/2)일 이상.
- 관광지와 식당은 날짜 사이에 중복되지 않는다.
- 사용자가 고정한 장소(state.pins)는 그 날짜에 둔다.

비용: 이동 분 + 0.5 x 대기 분 + 식당 점수 차이 x restaurant_lambda (+ 식당 후보가 없으면 가산).
이동 수단(도보/택시)과 시간은 모든 구간에 ctx.leg(= travel_leg)를 쓴다.

못 푸는 경우: 중복 허용 -> 한식 조건 완화 -> 장소 제외 순서로 완화하고 그 사실을 안내한다.
이 모듈이 다루지 못하는 입력(하루 4곳을 넘게 고정한 경우)은 ComposeUnsupported로 알려서 기존 방식으로 넘어간다.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Callable

from src.planner.geo import haversine_km
from src.planner.hours import earliest_start, hhmm_to_min, intervals_for
from src.planner.meals import is_korean, pinned_restaurant, restaurant_ok, restaurant_score
from src.planner.schema import Unscheduled


class ComposeUnsupported(Exception):
    """이 모듈이 다루지 않는 입력. 호출한 쪽이 기존 방식으로 처리한다."""


@dataclass
class DayChoice:
    subset: frozenset
    order: tuple
    modes: dict
    shortened: list          # 피로 예산을 맞추려고 짧은 코스로 바꾼 장소
    fatigue: int
    cost: float
    travel: int
    wait: int
    end: int
    events: list
    legs: list               # (출발 id, 도착 id, 분, 'walk'|'taxi')
    lunch: dict | None
    dinner: dict | None
    rests: frozenset = field(init=False)     # 이 하루에 쓰는 식당 id (겹침 검사용, 한 번만 계산)
    korean: int = field(init=False)          # 한식 끼니 수

    def __post_init__(self):
        self.rests = frozenset(m["pid"] for m in (self.lunch, self.dinner) if m and m["pid"])
        self.korean = sum(1 for m in (self.lunch, self.dinner) if m and m["ko"])


@dataclass
class Composition:
    assignment: dict[int, list[str]]
    modes: dict[int, dict[str, str]]
    meal_pins: dict[str, str]
    unscheduled: list[Unscheduled]
    notes: list[str]
    plans: dict[int, DayChoice] = field(default_factory=dict)


class Composer:
    def __init__(self, ctx, select_modes: Callable):
        self.ctx = ctx
        self.select_modes = select_modes
        self.cfg = ctx.settings["compose"]
        self.F = ctx.profile.fatigue_budget
        meal = ctx.settings["meal"]
        self.lunch = (hhmm_to_min(meal["lunch_earliest"]), hhmm_to_min(meal["lunch_latest_start"]))
        self.dinner = (hhmm_to_min(meal["dinner_earliest"]), hhmm_to_min(meal["dinner_latest_start"]))
        self.eat = meal["duration_min"]
        self.allow = meal["travel_allowance_min"]
        self.rest = ctx.rest
        self.reserved = set(ctx.state.meal_pins.values()) | set(ctx.state.excluded_restaurants)
        self.in_site = set(ctx.settings["in_site_meal_places"])
        self._plans: dict[frozenset, list[DayChoice]] = {}
        self._opts: dict[tuple, tuple] = {}
        self._static: dict[tuple, list] = {}

    # ── 장소 방식과 피로 ──────────────────────────────────────

    def modes_for(self, subset):
        """(방식, 점수 합, 예산 때문에 짧게 바꾼 장소). 예산을 못 맞추면 None."""
        ctx, pls = self.ctx, self.ctx.places
        snapshot = list(ctx.assumptions)
        base = self.select_modes(list(subset), ctx)       # 안내 문구는 후보마다 쌓이지 않게 되돌린다
        ctx.assumptions[:] = snapshot
        free = [p for p in subset if p not in ctx.state.mode_overrides and base[p] != "short"]
        masks = sorted(range(1 << len(free)), key=lambda m: bin(m).count("1"))
        for mask in masks:
            modes = dict(base)
            changed = [free[i] for i in range(len(free)) if mask >> i & 1]
            for p in changed:
                modes[p] = "short"
            fat = sum(pls[p].modes[modes[p]]["score"] for p in subset)
            if fat <= self.F:
                return modes, fat, changed
        return None

    # ── 식당 후보 (기존 choose_restaurant 규칙과 같은 필터, 한 곳이 아니라 상위 여러 곳) ──

    def _placeholder(self, loc, t, window, penalty):
        eat_start = max(t, window[0])
        if eat_start > window[1]:
            return None
        return dict(pid=None, name=None, coord=loc, score=0.0, ko=False, eat_start=eat_start, move=0, how="walk",
                    placeholder=True, penalty=penalty, rating=None, rating_count=None, tags=None, venue=None,
                    local=False)

    def _near(self, loc, radius):
        """위치와 반경이 같으면 시각과 무관한 후보(프로필 조건, 거리, 이동 시간)를 한 번만 계산한다."""
        key = (loc, radius)
        if key not in self._static:
            ctx, cfg = self.ctx, self.ctx.settings["restaurant"]
            out = []
            for pid, r in self.rest.by_id.items():
                if pid in self.reserved or not restaurant_ok(r, ctx.profile, cfg):
                    continue
                xy = (r["lat"], r["lng"])
                dist = haversine_km(loc, xy)
                if dist > radius:
                    continue
                mins, how = ctx.leg(loc, xy)
                if mins > self.allow:
                    continue
                out.append((pid, r, xy, mins, how, restaurant_score(r, dist, ctx.profile, cfg)))
            self._static[key] = out
        return self._static[key]

    def meal_options(self, loc, t, kind):
        key = (loc, t, kind)
        if key in self._opts:
            return self._opts[key]
        ctx, cfg = self.ctx, self.ctx.settings["restaurant"]
        window = self.lunch if kind == "lunch" else self.dinner
        result: tuple = ([], None)
        if not self.rest.available:
            ph = self._placeholder(loc, t, window, 0.0)
            result = ([ph], 0.0) if ph else ([], None)
        else:
            for radius in cfg["search_radius_km"]:
                out = []
                for pid, r, xy, mins, how, score in self._near(loc, radius):
                    eat_start = max(t + mins, window[0])
                    if eat_start > window[1]:
                        continue
                    hours = self.rest.hours.get(pid)
                    if hours is not None and earliest_start(intervals_for(hours, None), eat_start, self.eat) != eat_start:
                        continue
                    out.append(dict(pid=pid, name=r["name"], coord=xy, score=score,
                                    ko=is_korean(r), eat_start=eat_start, move=mins, how=how, placeholder=False,
                                    penalty=0.0, rating=r.get("rating"), rating_count=r.get("rating_count"),
                                    tags=r.get("ingredient_tags"), venue=r.get("venue_type"), local=bool(r.get("is_local"))))
                if out:
                    out.sort(key=lambda x: -x["score"])
                    top = out[: self.cfg["top_restaurants"]]
                    top += [x for x in out if x["ko"] and x not in top][: self.cfg["top_korean"]]
                    result = (top, out[0]["score"])
                    break
            else:
                ph = self._placeholder(loc, t, window, self.cfg["placeholder_penalty"])
                result = ([ph], 0.0) if ph else ([], None)
        self._opts[key] = result
        return result

    # ── 하루 후보 만들기 ─────────────────────────────────────

    def plans_of(self, subset: frozenset) -> list[DayChoice]:
        if subset not in self._plans:
            self._plans[subset] = self._build(subset)
        return self._plans[subset]

    def _build(self, subset: frozenset) -> list[DayChoice]:
        got = self.modes_for(subset)
        if got is None:
            return []
        modes, fat, shortened = got
        plans: list[DayChoice] = []
        for order in itertools.permutations(sorted(subset)):
            site = [p for p in order if p in self.in_site]
            positions = [order.index(site[0])] if site else range(-1, len(order))
            for lunch_pos in positions:
                plans += self._run(order, lunch_pos, modes, fat, shortened, bool(site))
        plans.sort(key=lambda p: p.cost)
        keep, seen = [], set()
        for p in plans:
            if p.rests in seen:
                continue
            seen.add(p.rests)
            keep.append(p)
            if len(keep) >= self.cfg["variants_per_subset"]:
                break
        keep += [p for p in plans if p.korean and p not in keep][:2]
        return keep

    def _run(self, order, lunch_pos, modes, fat, shortened, in_site) -> list[DayChoice]:
        ctx, pls = self.ctx, self.ctx.places
        lam = self.cfg["restaurant_lambda"]

        def init():
            return dict(t=ctx.w_start, loc=ctx.base, lid="base", travel=0, wait=0, events=[], legs=[], pen=0.0)

        def visit(st, pid):
            pl = pls[pid]
            mins, how = ctx.leg(st["loc"], pl.coord)
            arrive = st["t"] + mins
            start = earliest_start(intervals_for(pl.hours, None), arrive, pl.stay_min)
            if start is None:
                return None
            return dict(st, t=start + pl.stay_min, loc=pl.coord, lid=pid, travel=st["travel"] + mins,
                        wait=st["wait"] + (start - arrive), events=st["events"] + [("관광", start, start + pl.stay_min, pid)],
                        legs=st["legs"] + [(st["lid"], pid, mins, how)])

        def eat(st, opt, label):
            arrive = st["t"] + opt["move"]
            ev = (label, opt["eat_start"], opt["eat_start"] + self.eat, opt["pid"])
            legs = st["legs"] + ([(st["lid"], opt["pid"], opt["move"], opt["how"])] if opt["move"] else [])
            return dict(st, t=opt["eat_start"] + self.eat, loc=opt["coord"], lid=opt["pid"] or st["lid"],
                        travel=st["travel"] + opt["move"], wait=st["wait"] + (opt["eat_start"] - arrive),
                        events=st["events"] + [ev], legs=legs, pen=st["pen"] + opt["penalty"])

        out: list[DayChoice] = []
        st = init()
        for pid in order[: lunch_pos + 1]:
            st = visit(st, pid)
            if st is None:
                return out
        if in_site:  # 관광지 안 고정 식당(바나힐 뷔페): 시간을 더 쓰지 않는다
            site = next(p for p in order if p in self.in_site)
            pick = pinned_restaurant(ctx.rest, site) if ctx.rest.available else None
            start = st["events"][-1][1]
            opt = dict(pid=pick.place_id if pick else None, name=pick.name if pick else None, coord=st["loc"], score=0.0,
                       ko=bool(pick and pick.is_korean), eat_start=start, move=0, how="walk", placeholder=pick is None,
                       penalty=0.0, rating=pick.rating if pick else None, rating_count=pick.rating_count if pick else None,
                       tags=None, venue=None, local=False)
            lunches, lbest = [opt], 0.0
        else:
            lunches, lbest = self.meal_options(st["loc"], st["t"], "lunch")
        for lo in lunches:
            if in_site:
                st2 = dict(st, events=st["events"] + [("점심", lo["eat_start"], lo["eat_start"] + self.eat, lo["pid"])])
            else:
                st2 = eat(st, lo, "점심")
            for pid in order[lunch_pos + 1:]:
                st2 = visit(st2, pid)
                if st2 is None:
                    break
            if st2 is None:
                continue
            far_exit = pls[order[-1]].cluster in ("west", "banahills")   # 먼 곳에서는 시내로 돌아와 저녁을 먹는다
            st3 = st2
            if far_exit:
                mins, how = ctx.leg(st2["loc"], ctx.base)
                st3 = dict(st2, t=st2["t"] + mins, loc=ctx.base, lid="base", travel=st2["travel"] + mins,
                           legs=st2["legs"] + [(st2["lid"], "base", mins, how)])
            dinners, dbest = self.meal_options(st3["loc"], st3["t"], "dinner")
            for do in dinners:
                if do["pid"] and do["pid"] == lo["pid"]:
                    continue
                st4 = eat(st3, do, "저녁")
                if st4["t"] > ctx.w_end:
                    continue
                back, how = ctx.leg(st4["loc"], ctx.base)
                cost = (st4["travel"] + back + 0.5 * st4["wait"] + st4["pen"]
                        + lam * ((lbest - lo["score"]) + ((dbest or 0.0) - do["score"])))
                out.append(DayChoice(frozenset(order), tuple(order), modes, shortened, fat, cost, st4["travel"] + back,
                                     st4["wait"], st4["t"], st4["events"], st4["legs"] + [(st4["lid"], "base", back, how)],
                                     lo, do))
        return out


# ── 날짜 나누기: 겹치지 않는 조합 찾기 ────────────────────────────

def _korean_days(ctx, nonempty_days: int) -> int:
    need = ctx.profile.korean_need
    if need == "daily":
        return nonempty_days
    if need == "every_2_3_days":
        return math.ceil(nonempty_days / 2)
    return 0


def _solve(cm: Composer, groups: list[tuple], pin_day: dict, n_days: int, cap: int, allow_repeat: bool, need_ko: bool):
    """groups: 같은 날로 고정된 장소 묶음(고정이 없으면 장소 하나). 비용이 가장 낮은 DayChoice 목록(하루 하나)을 돌려준다.

    남은 묶음을 d일에 나눌 때 드는 최소 비용(식당 겹침·한식은 무시한 하한)을 부분집합 표로 미리 구해서
    가망 없는 가지를 일찍 자른다."""
    ctx, pls = cm.ctx, cm.ctx.places
    m = len(groups)
    target_days = min(n_days, m)      # 가능하면 모든 날을 쓴다. 못 쓰면 빈 날마다 벌점
    nodes, best = [0], [None]
    limit = cm.cfg["node_limit"]
    bal, empty_pen = cm.cfg["balance_weight"], cm.cfg["empty_day_penalty"]
    INF = float("inf")

    def pinned_day_of(members):
        days = {pin_day[p] for p in members if p in pin_day}
        return (next(iter(days)) if len(days) == 1 else None) if days else 0

    infos: dict[int, tuple | None] = {}

    def info(mask):
        """(구성원, 고정 날짜, 최소 비용). 만들 수 없는 조합이면 None."""
        if mask not in infos:
            members = tuple(itertools.chain.from_iterable(groups[i] for i in range(m) if mask >> i & 1))
            ok = len(members) <= cap
            if ok and len(members) > 1 and any(pls[p].solo for p in members) and not any(p in pin_day for p in members):
                ok = False  # 단독 장소는 혼자 하루를 쓴다. 사용자가 같은 날로 고정한 경우만 예외
            pd = pinned_day_of(members) if ok else None
            if not ok or pd is None:
                infos[mask] = None
            else:
                plans = cm.plans_of(frozenset(members))
                infos[mask] = (members, pd, min((p.cost for p in plans), default=INF))
        return infos[mask]

    lb_memo: dict[tuple, float] = {}

    def lb(mask, days_left):
        if mask == 0:
            return 0.0
        if days_left == 0:
            return INF
        key = (mask, days_left)
        if key not in lb_memo:
            low = mask & -mask
            rest = mask ^ low
            out, sub = INF, rest
            while True:
                S = low | sub
                got = info(S)
                if got and got[2] < INF:
                    out = min(out, got[2] + lb(mask & ~S, days_left - 1))
                if sub == 0:
                    break
                sub = (sub - 1) & rest
            lb_memo[key] = out
        return lb_memo[key]

    ko_cache: dict[int, int] = {}

    def ko_count(plan):
        if id(plan) not in ko_cache:
            ko_cache[id(plan)] = _ko_count(plan)
        return ko_cache[id(plan)]

    def _ko_count(plan):
        """한식 끼니 수. 이미 고정된 식당이 있는 끼니는 그 식당의 실제 한식 여부를 쓴다(고정한 날을 바꾸지 않기 위해)."""
        day = pinned_day_of(plan.subset)
        if not day:
            return plan.korean
        n = 0
        for kind, meal in (("lunch", plan.lunch), ("dinner", plan.dinner)):
            pin = ctx.state.meal_pins.get(f"{day}:{kind}")
            n += int(is_korean(cm.rest.by_id[pin])) if pin and pin in cm.rest.by_id else int(bool(meal and meal["ko"]))
        return n

    need_total = _korean_days(ctx, target_days) if need_ko else 0

    def dfs(remaining, chosen, used_r, pin_days, spent, ko_days):
        nodes[0] += 1
        if nodes[0] > limit:
            return
        if remaining == 0:
            need = _korean_days(ctx, len(chosen)) if need_ko else 0
            if ko_days < need:
                return
            sizes = [len(p.subset) for p in chosen]
            total = spent + bal * (max(sizes) - min(sizes)) + empty_pen * max(0, target_days - len(chosen))
            if best[0] is None or total < best[0][0]:
                best[0] = (total, list(chosen))
            return
        days_left = n_days - len(chosen)
        if days_left <= 0:
            return
        plans_left = min(days_left, bin(remaining).count("1"))      # 앞으로 더 만들 수 있는 하루의 최대 수
        if need_total - ko_days > plans_left:                          # 남은 날을 모두 한식으로 채워도 모자람
            return
        if best[0] is not None and spent + lb(remaining, days_left) >= best[0][0]:
            return
        low = remaining & -remaining
        rest = remaining ^ low
        cands, sub = [], rest
        while True:
            S = low | sub
            got = info(S)
            after = remaining & ~S
            if got and got[2] < INF and sum(len(groups[i]) for i in range(m) if after >> i & 1) <= cap * (days_left - 1):
                cands.append((got[2] + lb(after, days_left - 1), S, after, got))
            if sub == 0:
                break
            sub = (sub - 1) & rest
        cands.sort(key=lambda c: c[0])
        for bound, S, after, (members, pd, _) in cands:
            if pd and pd in pin_days:
                continue
            if best[0] is not None and spent + bound >= best[0][0]:
                break
            must_ko = need_total - ko_days >= plans_left            # 남은 하루가 전부 한식이어야 하는 경우
            for plan in cm.plans_of(frozenset(members)):
                if not allow_repeat and (plan.rests & used_r):
                    continue
                k = 1 if ko_count(plan) else 0
                if must_ko and not k:
                    continue
                dfs(after, chosen + [plan], used_r | plan.rests, pin_days | ({pd} if pd else set()), spent + plan.cost,
                    ko_days + k)

    dfs((1 << m) - 1, [], frozenset(), frozenset(), 0.0, 0)
    return best[0]


def _match_days(ctx, plans: list[DayChoice], n_days: int, pin_day: dict):
    """플랜을 날짜에 놓는다. 고정된 장소가 있으면 그 날짜에, 나머지는 앞쪽 날부터 휴무 충돌이 적게."""
    fixed, free = {}, []
    for p in plans:
        days = {pin_day[x] for x in p.subset if x in pin_day}
        if days:
            fixed[next(iter(days))] = p
        else:
            free.append(p)
    free_days = [d for d in range(1, n_days + 1) if d not in fixed][: len(free)]

    def closed(plan, day):
        wd = ctx.weekday(day - 1)
        return sum(1 for x in plan.subset if not intervals_for(ctx.places[x].hours, wd))

    rank = {c: i for i, c in enumerate(ctx.settings["clusters"]["order"])}

    def sort_key(plan):  # 가까운 권역(시내)이 앞, 먼 곳(바나힐)은 뒤
        return (min(rank.get(ctx.places[x].cluster, 99) for x in plan.subset), sorted(plan.subset)[0])

    free.sort(key=sort_key)
    if len(free) <= 6:
        def key(perm):
            inversions = sum(1 for i in range(len(perm)) for j in range(i + 1, len(perm))
                             if free.index(perm[i]) > free.index(perm[j]))
            return (sum(closed(p, d) for p, d in zip(perm, free_days)), inversions)
        best = min(itertools.permutations(free), key=key)
    else:
        best = tuple(free)
    result = dict(fixed)
    result.update(dict(zip(free_days, best)))
    return result


def compose_days(ctx, place_ids: list[str], n_days: int, select_modes: Callable) -> Composition:
    cm = Composer(ctx, select_modes)
    cfgf = ctx.settings["fatigue"]
    pool = list(dict.fromkeys(place_ids))
    pin_day = {p: d for p, d in ctx.state.pins.items() if p in pool and 1 <= d <= n_days}
    by_day: dict[int, list[str]] = {}
    for p in pool:
        if p in pin_day:
            by_day.setdefault(pin_day[p], []).append(p)
    if any(len(g) > cfgf["max_places_per_day_explicit"] for g in by_day.values()):
        raise ComposeUnsupported("하루에 고정된 장소가 최대치를 넘습니다.")
    groups_all = [tuple(g) for _, g in sorted(by_day.items())] + [(p,) for p in pool if p not in pin_day]
    skippable = [g for g in groups_all if not any(p in pin_day for p in g)]
    attempts = [(cfgf["max_places_per_day"], False, True), (cfgf["max_places_per_day_explicit"], False, True),
                (cfgf["max_places_per_day"], True, True), (cfgf["max_places_per_day_explicit"], True, True),
                (cfgf["max_places_per_day"], True, False), (cfgf["max_places_per_day_explicit"], True, False)]
    notes: list[str] = []
    found = None
    for k in range(len(skippable) + 1):
        # 우선순위: 모든 날을 쓴다 > 식당 중복 금지 > 한식. 모든 날을 쓰는 해가 없을 때만 빈 날이 있는 해를 받아들인다.
        partial = None
        for idx, (cap, repeat, ko) in enumerate(attempts):
            best_here = None
            for skip in itertools.combinations(skippable, k):
                groups = [g for g in groups_all if g not in skip]
                if not groups:
                    continue
                sol = _solve(cm, groups, pin_day, n_days, cap, repeat, ko)
                if sol and (best_here is None or sol[0] < best_here[0][0]):
                    best_here = (sol, skip, idx, cap, min(n_days, len(groups)) - len(sol[1]))
            if best_here is None:
                continue
            if best_here[4] == 0:
                found = best_here
                break
            if partial is None or best_here[4] < partial[4]:
                partial = best_here
        found = found or partial
        if found:
            break
    if found is None:  # 고정한 장소만으로도 구성할 수 없는 경우: 전부 미배치로 보내지 않고 기존 방식에 맡긴다
        raise ComposeUnsupported("고정한 장소로 하루를 구성할 수 없습니다.")
    (total, plans), skip, idx, cap, _empties = found
    if idx >= 2:
        notes.append("식당이 겹치지 않게 배치할 수 없어 일부 끼니의 식당이 다른 날과 같을 수 있습니다.")
    if idx >= 4:
        notes.append("한식 빈도를 모두 채울 수 있는 구성이 없어 한식이 일부 줄었습니다.")
    placed = _match_days(ctx, plans, n_days, pin_day)
    names = {pid: pl.name for pid, pl in ctx.places.items()}
    assignment = {d: list(placed[d].order) if d in placed else [] for d in range(1, n_days + 1)}
    modes = {d: dict(placed[d].modes) for d in placed}
    meal_pins: dict[str, str] = {}
    for d, plan in placed.items():
        for kind, meal in (("lunch", plan.lunch), ("dinner", plan.dinner)):
            key = f"{d}:{kind}"
            if meal and meal["pid"] and key not in ctx.state.meal_pins:
                meal_pins[key] = meal["pid"]
        for pid in plan.shortened:
            notes.append(f"하루 피로 예산({cm.F})을 맞추려고 {names[pid]}은(는) "
                         f"'{ctx.places[pid].modes['short']['name']}' 코스로 잡았습니다.")
    reason = (f"하루 피로 예산(점수 합 {cm.F})과 하루 최대 {cap}곳 안에서 배치할 수 없습니다. "
              "일수를 늘리거나 장소를 줄여 주세요.")
    unscheduled = [Unscheduled(place_id=p, reason=reason) for g in skip for p in g]
    for plan in placed.values():  # 방식 선택 안내 문구(보행 한도가 짧아 짧은 코스로 잡은 장소 등)를 남긴다
        select_modes(list(plan.order), ctx)
    return Composition(assignment, modes, meal_pins, unscheduled, notes, placed)
