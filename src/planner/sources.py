"""관광지·식당·설정 데이터 로딩. 일정 엔진은 이 모듈을 통해서만 데이터를 읽는다."""

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from src.planner.hours import Hours, hhmm_to_min, parse_google_hours, parse_korean_hours
from src.planner.stay import load_config as load_stay_config
from src.planner.stay import resolve_stay, stay_minutes
from src.scoring.visit_modes import load_modes

ROOT = Path(__file__).resolve().parents[2]
PLANNER_DIR = Path(__file__).resolve().parent
DEFAULT_RESTAURANTS = ROOT / "data" / "restaurants" / "restaurants_danang.json"


@lru_cache
def load_settings() -> dict:
    return json.loads((PLANNER_DIR / "config.json").read_text(encoding="utf-8"))


@dataclass
class Place:
    id: str
    name: str
    lat: float
    lng: float
    region: str
    cluster: str
    solo: bool
    stay_min: int
    stay_source: str
    modes: dict
    status: str
    hours: Hours | None
    hours_source: str
    hours_confidence: str | None = None
    types: list[str] = field(default_factory=list)
    evening: bool = False

    @property
    def coord(self) -> tuple[float, float]:
        return (self.lat, self.lng)


def _manual_hours(entry: dict) -> Hours:
    intervals = [(hhmm_to_min(a), hhmm_to_min(b)) for a, b in entry["intervals"]]
    return {d: list(intervals) for d in range(7)}


@lru_cache
def load_places() -> dict[str, Place]:
    settings = load_settings()
    cl = settings["clusters"]
    profile = json.loads((PLANNER_DIR / "attraction_profile.json").read_text(encoding="utf-8"))["places"]
    manual = json.loads((PLANNER_DIR / "attraction_hours.json").read_text(encoding="utf-8"))["places"]
    attractions = {a["id"]: a for a in json.loads(
        (ROOT / "data" / "scoring" / "attractions.json").read_text(encoding="utf-8"))}
    catalog = load_modes()
    stay_cfg = load_stay_config()

    places: dict[str, Place] = {}
    for pid, prof in profile.items():
        att = attractions[pid]
        hours = parse_google_hours(att.get("google", {}).get("hours"))
        source, confidence = "google", None
        if hours is None and pid in manual:
            hours, source, confidence = _manual_hours(manual[pid]), "manual", manual[pid]["confidence"]
        elif hours is None:
            source = "unknown"
        level, stay_source = resolve_stay(prof, stay_cfg)
        cluster = cl["place_cluster_override"].get(pid) or cl["region_to_cluster"][prof["region"]]
        evening_from = hhmm_to_min(cl["evening_open_at_or_after"])
        starts = [s for ints in (hours or {}).values() for s, _ in ints]
        places[pid] = Place(
            id=pid, name=att["name_ko"], lat=att["lat"], lng=att["lng"],
            region=prof["region"], cluster=cluster, solo=pid in cl["solo_places"],
            stay_min=stay_minutes(level, stay_cfg), stay_source=stay_source,
            modes=catalog[pid]["modes"], status=catalog[pid]["status"],
            hours=hours, hours_source=source, hours_confidence=confidence,
            types=prof.get("types", []),
            evening=bool(starts) and min(starts) >= evening_from,
        )
    return places


@dataclass
class Restaurants:
    """희윤님 식당 JSON(attractions[].restaurants[]). 파일이 없으면 available=False."""

    available: bool = False
    by_id: dict[str, dict] = field(default_factory=dict)
    pinned: dict[str, str] = field(default_factory=dict)
    hours: dict[str, Hours | None] = field(default_factory=dict)


def load_restaurants(path: str | Path | None = None) -> Restaurants:
    path = Path(path or os.getenv("RESTAURANTS_JSON") or DEFAULT_RESTAURANTS)
    if not path.exists():
        return Restaurants()
    data = json.loads(path.read_text(encoding="utf-8"))
    result = Restaurants(available=True)
    for block in data.get("attractions", []):
        aid = block["attraction"]["id"]
        for r in block.get("restaurants", []):
            pid = r["place_id"]
            if pid not in result.by_id:
                result.by_id[pid] = r
                result.hours[pid] = parse_korean_hours(r.get("opening_text"))
            if r.get("pinned") and aid not in result.pinned:
                result.pinned[aid] = pid
    return result
