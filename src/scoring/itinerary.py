"""Require a confirmed tour route before treating visit-mode scores as a package."""
from src.scoring.package_difficulty import calculate_package


def evaluate_itinerary(days, catalog):
    """Each stop needs place_id, mode, source_ref, and route_note from the itinerary."""
    for day in days:
        for stop in day:
            place_id = stop.get("place_id")
            mode_id = stop.get("mode")
            if place_id not in catalog or mode_id not in catalog[place_id]["modes"]:
                raise ValueError(f"Unmapped attraction or visit mode: {place_id}/{mode_id}")
            if not stop.get("source_ref") or not stop.get("route_note"):
                raise ValueError(f"Route evidence required: {place_id}/{mode_id}")
    result = calculate_package(days, catalog)
    result["review_required"] = sorted({stop["place_id"] for day in days for stop in day
                                         if catalog[stop["place_id"]]["status"] != "ok"})
    result["route_evidence"] = [{"day": i, "place_id": stop["place_id"],
                                  "mode": stop["mode"], "source_ref": stop["source_ref"],
                                  "route_note": stop["route_note"]}
                                 for i, day in enumerate(days, 1) for stop in day]
    result["status"] = "needs_review" if result["review_required"] else "calculated"
    return result
