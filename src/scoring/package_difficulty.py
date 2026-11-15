"""Pure package difficulty calculation from named attraction visit modes."""
from src.scoring.verify import round_half_up


def calculate_package(days, catalog):
    """days: [[{place_id, mode}, ...], ...], in visit order.

    A day adds one point per adjacent pair of demanding visits (score >= 6),
    capped at two bonus points. A package reports the hardest day and mean day.
    """
    if not days or any(not day for day in days):
        raise ValueError("Package needs at least one nonempty day")
    result = []
    for index, day in enumerate(days, 1):
        visits = []
        for item in day:
            place_id, mode_id = item["place_id"], item["mode"]
            place = catalog[place_id]
            mode = place["modes"][mode_id]
            visits.append({"place_id": place_id, "name_ko": place["name_ko"],
                           "mode": mode_id, "mode_name": mode["name"], "score": mode["score"]})
        demanding_pairs = sum(a["score"] >= 6 and b["score"] >= 6
                              for a, b in zip(visits, visits[1:]))
        bonus = min(2, demanding_pairs)
        result.append({"day": index, "visits": visits, "base": max(v["score"] for v in visits),
                       "consecutive_bonus": bonus,
                       "difficulty": min(10, max(v["score"] for v in visits) + bonus)})
    daily = [d["difficulty"] for d in result]
    return {"days": result, "peak": max(daily), "mean": round(sum(daily) / len(daily), 1),
            "mean_rounded": round_half_up(sum(daily) / len(daily))}
