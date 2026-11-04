import json
import os
from pathlib import Path

# HITL 임시 점수 파일(로컬 시연용)이 테스트 결과에 섞이지 않게 한다
os.environ.setdefault("SCORING_OVERRIDES_JSON", str(Path(__file__).resolve().parent / "_no_overrides.json"))

import pytest

from src.planner.sources import load_restaurants
from src.profile.schema import ParentProfileInput
from src.profile.service import build_profile

ROOT = Path(__file__).resolve().parents[1]
DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


def _hours(open_text: str = "오전 10:00 ~ 오후 9:00") -> list[str]:
    return [f"{d}요일: {open_text}" for d in DAY_NAMES]


def _restaurant(aid, suffix, name, ptype, rating, count, lat, lng, **extra):
    return {
        "place_id": f"{aid}-{suffix}", "name": name, "lat": lat, "lng": lng, "primary_type": ptype,
        "cuisine_tag": "other", "is_korean": extra.pop("korean", False), "is_local": extra.pop("local", False),
        "rating": rating, "rating_count": count, "price_level": None,
        "opening_text": extra.pop("hours", _hours()), "hours_unknown": False, "distance_m": 100,
        "score": rating, "reviews": {"korean_reviews": []}, "pinned": extra.pop("pinned", False),
    }


@pytest.fixture(scope="session")
def restaurants(tmp_path_factory):
    """희윤님 JSON 형식을 흉내 낸 합성 식당 데이터. 선택·제외 규칙을 검증하려고 종류별로 섞어 둔다."""
    attractions = json.loads((ROOT / "data" / "scoring" / "attractions.json").read_text(encoding="utf-8"))
    blocks = []
    for a in attractions:
        aid, lat, lng = a["id"], a["lat"], a["lng"]
        if aid == "dad-01":
            buffet = _restaurant(aid, "buffet", "포 시즌스 뷔페 레스토랑 (바나 힐)", "buffet_restaurant", 3.2, 1006,
                                 15.9957, 107.9903, pinned=True, hours=_hours("오전 10:30 ~ 오후 3:00"))
            blocks.append({"attraction": {"id": aid, "name": a["name_ko"], "lat": lat, "lng": lng},
                           "restaurants": [buffet]})
            continue
        items = [
            _restaurant(aid, "local1", f"로컬식당1 {aid}", "vietnamese_restaurant", 4.8, 500, lat + .002, lng + .002, local=True),
            _restaurant(aid, "local2", f"로컬식당2 {aid}", "vietnamese_restaurant", 4.6, 300, lat - .002, lng + .002, local=True),
            _restaurant(aid, "kor", f"한식당 {aid}", "korean_restaurant", 4.7, 300, lat + .003, lng, korean=True),
            _restaurant(aid, "sea", f"해산물 {aid}", "seafood_restaurant", 5.0, 900, lat, lng + .003),
            _restaurant(aid, "hotel", f"호텔 {aid}", "resort_hotel", 4.9, 3000, lat, lng - .002),
            _restaurant(aid, "new", f"신규 {aid}", "vietnamese_restaurant", 5.0, 2, lat, lng),
        ]
        blocks.append({"attraction": {"id": aid, "name": a["name_ko"], "lat": lat, "lng": lng}, "restaurants": items})
    path = tmp_path_factory.mktemp("restaurants") / "restaurants.json"
    path.write_text(json.dumps({"city": "다낭", "attractions": blocks}, ensure_ascii=False), encoding="utf-8")
    return load_restaurants(path)


@pytest.fixture
def make_profile():
    def _make(**kwargs):
        defaults = {"age": 68, "gender": "female"}
        return build_profile(ParentProfileInput(**{**defaults, **kwargs}))
    return _make
