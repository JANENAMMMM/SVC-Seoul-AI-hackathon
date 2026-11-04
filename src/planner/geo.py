import math


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def travel_minutes(a: tuple[float, float], b: tuple[float, float], travel_cfg: dict) -> int:
    """직선거리 × 도로 보정 ÷ 평균 속도. 같은 장소면 0분."""
    km = haversine_km(a, b)
    if km < travel_cfg["same_place_km"]:
        return 0
    minutes = km * travel_cfg["road_factor"] / travel_cfg["avg_speed_kmh"] * 60
    return max(travel_cfg["min_minutes"], round(minutes))


def travel_leg(a: tuple[float, float], b: tuple[float, float], speed_mps: float, travel_cfg: dict,
               walk_cap_min: int) -> tuple[int, str]:
    """(분, 'walk'|'taxi'). 도보가 짧고 연속 보행 한도 안이면 걷고, 아니면 택시를 탄다."""
    km = haversine_km(a, b)
    if km < travel_cfg["same_place_km"]:
        return 0, "walk"
    walk_min = km * 1000 * travel_cfg["walk_road_factor"] / speed_mps / 60
    if walk_min <= min(travel_cfg["walk_max_min"], walk_cap_min):
        return max(1, round(walk_min)), "walk"
    return travel_minutes(a, b, travel_cfg), "taxi"
