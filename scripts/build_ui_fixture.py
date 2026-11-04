"""Generate reproducible demo from recorded scoring evidence and the real planner (no LLM)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.ui import catalog, evidence_detail, share_snapshot, source_records
from src.profile.schema import ParentProfileInput
from src.profile.service import build_profile
from src.planner.schema import PlanRequest, PlanState, LatLng, SetMode, RemovePlace, LightenDay, MoreKoreanMeals
from src.planner.sources import load_places
from src.planner.engine import build_itinerary
from src.planner.edit import refine
from src.database import connect_db


def main():
    profile = build_profile(ParentProfileInput(age=64, gender="female", walking_duration="15_30min", korean_need="daily"))
    start = load_places()["dad-02"]
    # Existing standard itinerary is the starting point; keep the attraction, change its visit mode.
    before = build_itinerary(PlanRequest(travelers=[profile], place_ids=["dad-02", "dad-03", "dad-05", "dad-06", "dad-09"], days=3,
                                        start_point=LatLng(lat=start.lat, lng=start.lng),
                                        state=PlanState(mode_overrides={"dad-02": "standard"})))
    after = refine(before, [SetMode(op="set_mode", place_id="dad-02", mode="short")])
    scenarios = {}
    for pid in before.request.place_ids:
        for op, command in (("set_mode", SetMode(op="set_mode", place_id=pid, mode="short")),
                            ("remove_place", RemovePlace(op="remove_place", place_id=pid))):
            scenarios[f"{op}:{pid}"] = refine(before, [command]).model_dump(mode="json")
    for day in before.days:
        scenarios[f"lighten_day:{day.day}"] = refine(before, [LightenDay(op="lighten_day", day=day.day)]).model_dump(mode="json")
    scenarios["more_korean_meals:"] = refine(before, [MoreKoreanMeals(op="more_korean_meals")]).model_dump(mode="json")
    places = catalog()
    evidence = {p["place_id"]: evidence_detail(p["place_id"]) for p in places}
    records = {}
    try:
        with connect_db() as conn:
            for pid in evidence:
                records[pid] = source_records(conn, pid)
    except Exception:
        print("Source DB unavailable; demo retains recorded IDs, conditions and source URLs only.")
    output = {"catalog": places, "evidence": evidence, "sources": records,
              "before": before.model_dump(mode="json"), "after": after.model_dump(mode="json"),
              "snapshot": share_snapshot(before.model_dump(mode="json"), "엄마"), "scenarios": scenarios,
              "provenance": "로컬 채점 기록과 실제 planner로 생성. 오행산에서 출발하는 기존 표준 관람 일정 조정 시나리오. 보행 응답 15~30분·엔진 한도 20분. 실시간 예보·유료 재채점·DB 쓰기 없음."}
    out = ROOT / "frontend/public/demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, default=str), encoding="utf-8")
    print("Fixture built: places=%d, runs=%d, mapped_dimensions=%d" % (len(places), sum(e["verification"]["runs"] for e in evidence.values()), sum(e["verification"]["matched_dimensions"] for e in evidence.values())))


if __name__ == "__main__":
    main()
