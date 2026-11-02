from src.scoring.engine import grade_site


def ev(basis, metric, value, unit="m", note=""):
    return {"basis": basis, "metric": metric, "value": value, "unit": unit, "source": "synthetic", "note": note}


def site(**dims):
    return {"id": "test", "name_ko": "시험", "dimensions": {f"D{i}": dims.get(f"D{i}", []) for i in range(1, 6)}}


def test_forced_high():
    g = grade_site(site(D2=[ev("B", "steps_count", 220, "steps")], D3=[ev("B", "transport_available", False, "bool")]))
    assert g["grade"] == "상" and "D2_high_no_full_relief" in g["rules_fired"]


def test_relief_lowers():
    g = grade_site(site(D2=[ev("B", "trail_gain_m", 70)], D3=[ev("B", "transport_available", True, "bool", "major_climb_replaced")]))
    assert g["grade"] == "중" and "relief_lowers_D2_1" in g["rules_fired"]


def test_heat_plus_one():
    climate = {"monthly_mean_apparent_max_c": {"7": 34}}
    g = grade_site(site(D2=[ev("B", "trail_gain_m", 30)], D4=[ev("B", "outdoor", True, "bool")]), climate)
    assert g["grade"] == "상" and "heat_plus_1" in g["rules_fired"]


def test_heat_flat_walk_flag_only():
    climate = {"monthly_mean_apparent_max_c": {"7": 34}}
    g = grade_site(site(D1=[ev("B", "internal_route_km", 1.5, "km")], D4=[ev("B", "outdoor", True, "bool")]), climate)
    assert g["grade"] == "중" and "heat_flag_low_exertion" in g["rules_fired"]


def test_highest_basis():
    g = grade_site(site(D1=[ev("C", "walking_share", .3, "ratio"), ev("A", "median_km", .5, "km")]))
    assert g["dimensions"]["D1"]["level"] == 0
    assert g["dimensions"]["D1"]["basis"] == "A"
    assert g["status"] == "needs_review"


def test_missing_needs_review():
    g = grade_site(site())
    assert g["status"] == "needs_review" and "D1_missing" in g["review_reasons"]


def test_threshold_scale():
    s = site(D1=[ev("B", "internal_route_km", 2.5, "km")])
    assert grade_site(s, scale=1)["grade"] == "중"
    assert grade_site(s, scale=.8)["grade"] == "상"


def test_withheld_without_core_evidence():
    g = grade_site(site())
    assert g["grade"] == "보류" and g["status"] == "needs_review"
