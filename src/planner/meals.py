"""식사 슬롯에 넣을 식당 선택. 희윤님 식당 JSON을 그대로 입력으로 쓴다."""

from src.planner.geo import haversine_km
from src.planner.hours import earliest_start, intervals_for
from src.planner.profile_merge import MergedProfile
from src.planner.schema import RestaurantPick
from src.planner.sources import Restaurants


def is_korean(r: dict) -> bool:
    """한식 여부. Claude 재판정 결과(is_korean_final)가 있으면 그것을, 없으면 Google 분류(is_korean)를 쓴다."""
    final = r.get("is_korean_final")
    return bool(r.get("is_korean") if final is None else final)


def _pick(r: dict, anchor: tuple[float, float], hours_unknown: bool, leg: tuple[int, str] | None = None) -> RestaurantPick:
    return RestaurantPick(
        travel_min=leg[0] if leg else None, transport=leg[1] if leg and leg[0] else None,
        place_id=r["place_id"], name=r["name"], primary_type=r.get("primary_type"),
        rating=r.get("rating"), rating_count=r.get("rating_count"),
        is_korean=is_korean(r), is_local=bool(r.get("is_local")),
        hours_unknown=hours_unknown,
        venue_type=r.get("venue_type"), ingredient_tags=r.get("ingredient_tags"),
        tag_confidence=r.get("tag_confidence"), tag_evidence=r.get("tag_evidence"),
        distance_km=round(haversine_km(anchor, (r["lat"], r["lng"])), 2),
    )


def pinned_restaurant(rest: Restaurants, attraction_id: str) -> RestaurantPick | None:
    pid = rest.pinned.get(attraction_id)
    if not pid:
        return None
    r = rest.by_id[pid]
    return _pick(r, (r["lat"], r["lng"]), hours_unknown=rest.hours.get(pid) is None)


def use_pinned_restaurant(rest: Restaurants, place_id: str, anchor: tuple[float, float], start: int, end: int,
                          weekday: int | None, leg, max_leg_min: int, profile: MergedProfile) -> RestaurantPick | None:
    """고정해 둔 식당을 이번 슬롯에도 쓸 수 있으면 반환한다(이동 거리·영업시간만 다시 확인)."""
    r = rest.by_id.get(place_id)
    if r is None or not tags_allow(r, profile):
        return None
    move = leg(anchor, (r["lat"], r["lng"]))
    if move[0] > max_leg_min:
        return None
    hours = rest.hours.get(place_id)
    eat_start = start + move[0]
    if hours is not None and earliest_start(intervals_for(hours, weekday), eat_start, end - start) != eat_start:
        return None
    return _pick(r, anchor, hours_unknown=hours is None, leg=move)


def tags_allow(r: dict, profile: MergedProfile) -> bool:
    """희윤님 태그(venue_type, ingredient_tags)로 프로필과 맞지 않는 식당을 거른다. 태그가 없으면 거르지 않는다."""
    venue = r.get("venue_type")
    if venue in ("restaurant", "street_food") and venue not in profile.venues:
        return False
    return not (profile.avoid_ingredients & set(r.get("ingredient_tags") or ()))


def choose_restaurant(rest: Restaurants, anchor: tuple[float, float], start: int, end: int,
                      weekday: int | None, profile: MergedProfile, settings: dict,
                      used: set[str], need_korean: bool, leg=None, max_leg_min: int = 10) -> RestaurantPick | None:
    """start~end는 식사 시간(이동 제외). leg(a, b) -> (분, 수단)으로 식당까지 이동을 계산한다."""
    cfg = settings["restaurant"]
    for radius in cfg["search_radius_km"]:
        best, best_score, best_move = None, None, None
        for pid, r in rest.by_id.items():
            if pid in used or r.get("primary_type") in cfg["excluded_types"]:
                continue
            if "seafood" in profile.avoid_ingredients and r.get("primary_type") in cfg["seafood_types"]:
                continue
            if not tags_allow(r, profile):
                continue
            rating, count = r.get("rating"), r.get("rating_count")
            if rating is None or rating < cfg["min_rating"] or (count or 0) < cfg["min_rating_count"]:
                continue
            if need_korean and not is_korean(r):
                continue
            dist = haversine_km(anchor, (r["lat"], r["lng"]))
            if dist > radius:
                continue
            move = leg(anchor, (r["lat"], r["lng"])) if leg else (0, "walk")
            if move[0] > max_leg_min:
                continue
            hours = rest.hours.get(pid)
            eat_start = start + move[0]
            if hours is not None and earliest_start(intervals_for(hours, weekday), eat_start, end - start) != eat_start:
                continue
            score = (r.get("score") or rating) - cfg["distance_penalty_per_km"] * dist
            if r.get("is_local"):
                score += {"adventurous": cfg["local_pref_bonus"], "familiar": -cfg["local_pref_bonus"]}.get(
                    profile.local_food, 0.0)
            if best_score is None or score > best_score:
                best, best_score, best_move = r, score, move
        if best:
            return _pick(best, anchor, hours_unknown=rest.hours.get(best["place_id"]) is None, leg=best_move)
    return None
