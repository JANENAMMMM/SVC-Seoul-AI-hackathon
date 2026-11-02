"""Deterministic grading from normalized evidence."""
import json
from pathlib import Path

from .features import DATA, read

THRESHOLDS = {"D1_km": (1, 3), "D1_ratio": (.10, .25),
              "D2_m": (15, 60), "D2_steps": (50, 200), "D2_ratio": (.10, .30),
              "D4_c": 32, "D5_ratio": (.15, .30)}
LABELS = ("하", "중", "상")


def level_for(dim, evidence, scale=1, climate=None, visit_month=7):
    metric, value, unit = evidence["metric"], evidence["value"], evidence["unit"]
    if dim == "D3":
        return int(bool(value)) if evidence["basis"] == "B" else int(value >= .1)
    if dim == "D4":
        if evidence["basis"] == "C":
            return None  # review heat mentions do not establish monthly temperature
        if not value:
            return 0
        temp = (climate or {}).get("monthly_mean_apparent_max_c", {}).get(str(visit_month))
        return None if temp is None else (2 if temp >= THRESHOLDS["D4_c"] * scale else 1)
    if dim == "D1":
        limits = THRESHOLDS["D1_ratio" if unit == "ratio" else "D1_km"]
    elif dim == "D2":
        limits = THRESHOLDS["D2_ratio" if unit == "ratio" else "D2_steps" if unit == "steps" else "D2_m"]
    else:
        limits = THRESHOLDS["D5_ratio"]
    return int(value >= limits[0] * scale) + int(value >= limits[1] * scale)


def grade_site(site, climate=None, visit_month=7, flag_only=True, scale=1):
    if not 1 <= visit_month <= 12:
        raise ValueError("visit_month must be 1..12")
    dimensions, reasons = {}, []
    for dim in (f"D{i}" for i in range(1, 6)):
        candidates = []
        for index, evidence in enumerate(site["dimensions"].get(dim, [])):
            level = level_for(dim, evidence, scale, climate, visit_month)
            if level is not None:
                candidates.append((evidence, level, index))
        if not candidates:
            dimensions[dim] = {"level": None, "evidence": "missing", "checks": []}
            reasons.append(f"{dim}_missing")
            continue
        candidates.sort(key=lambda x: ("ABC".index(x[0]["basis"]), -x[1], x[2]))
        selected, level, _ = candidates[0]
        record = {"level": level, "basis": selected["basis"], "metric": selected["metric"],
                  "value": selected["value"], "unit": selected["unit"], "source": selected["source"],
                  "note": selected.get("note", ""), "checks": []}
        if dim == "D4" and selected["basis"] == "B" and selected["value"]:
            record["apparent_temperature_max_c"] = (climate or {}).get("monthly_mean_apparent_max_c", {}).get(str(visit_month))
        if selected["basis"] == "C":
            record["evidence"] = "weak"
        for other, other_level, _ in candidates[1:]:
            agree = abs(other_level - level) < 2
            record["checks"].append({"basis": other["basis"], "metric": other["metric"],
                                     "value": other["value"], "level": other_level, "agree": agree})
            if not agree:
                reasons.append(f"{dim}_evidence_disagreement")
        dimensions[dim] = record
    d = {k: v["level"] for k, v in dimensions.items()}
    base = max(d["D1"] or 0, d["D2"] or 0)
    rules = ["base_max_D1_D2"]
    relief = dimensions["D3"]
    full_relief = relief.get("level") == 1 and relief.get("note") == "major_climb_replaced"
    if d["D2"] == 2 and relief.get("level") == 0:
        score = 2
        rules.append("D2_high_no_full_relief")
    else:
        if full_relief and d["D2"] is not None:
            base = max(d["D1"] or 0, max(0, d["D2"] - 1))
            rules.append("relief_lowers_D2_1")
        score = base
        # heat aggravates climbing (high MET) outdoors; flat walking in heat is flagged only
        if d["D4"] == 2 and (d["D2"] or 0) >= 1:
            score = min(2, score + 1)
            rules.append("heat_plus_1")
        elif d["D4"] == 2:
            rules.append("heat_flag_low_exertion")
        if d["D5"] == 2:
            if flag_only:
                rules.append("D5_high_flag_only")
            elif score < 2:
                score += 1
                rules.append("D5_plus_1")
    return {"id": site["id"], "name_ko": site["name_ko"], "grade": LABELS[score],
            "grade_score": score, "dimensions": dimensions, "rules_fired": rules,
            "status": "needs_review" if reasons else "draft", "review_reasons": sorted(set(reasons)),
            "rubric_version": "1.0", "visit_month": visit_month}


def grade_all(features=None, visit_month=7, flag_only=True, scale=1, write=True):
    features = features if features is not None else read("features.json", [])
    climate = read("derived/climate_danang.json", {})
    grades = [grade_site(s, climate, visit_month, flag_only, scale) for s in features]
    if write:
        (DATA / "grades.json").write_text(json.dumps(grades, ensure_ascii=False, indent=2), encoding="utf-8")
    return grades
