from src.scoring.verify import aggregate, composite, grade_display, verify_run, web_id


def dim(t, lo, up, ids=("fact:x:steps_count",), lc=None, uc=None):
    return {"typical": t, "lower": lo, "upper": up, "evidence_ids": list(ids), "rationale": "",
            "lower_conditions": lc if lc is not None else ([{"condition": "엘리베이터", "evidence_ids": list(ids)}] if lo != t else []),
            "upper_conditions": uc if uc is not None else ([{"condition": "한낮", "evidence_ids": list(ids)}] if up != t else [])}


def out(**over):
    d = {k: dim(5, 4, 7) for k in ("climb", "walking", "heat", "crowd")}
    d.update(over)
    return {"dimensions": d, "confidence": "medium", "numeric_claims": []}


KNOWN = {"fact:x:steps_count", "gps:x:median_km"}
VALUES = {"fact:x:steps_count": 156, "gps:x:median_km": 1.7}


def test_composite_weights_and_rounding():
    dims = {"climb": {"typical": 8, "lower": 4, "upper": 9}, "walking": {"typical": 6, "lower": 5, "upper": 7},
            "heat": {"typical": 7, "lower": 4, "upper": 8}, "crowd": {"typical": 4, "lower": 3, "upper": 6}}
    # (24+18+14+4)/9=6.67 -> 7 ; (12+15+8+3)/9=4.22 -> 4 ; (27+21+16+6)/9=7.78 -> 8
    assert composite(dims) == {"typical": 7, "lower": 4, "upper": 8}
    assert composite({"climb": {"typical": None}}) ["typical"] is None


def test_grade_display():
    assert [grade_display(x) for x in (1, 3, 4, 5, 6, 10)] == ["하", "하", "중", "중", "상", "상"]


def test_valid_run():
    rep, ok = verify_run(out(), KNOWN, VALUES)
    assert ok and all(r["valid"] for r in rep.values())


def test_invalid_citation_invalidates_dimension_only():
    rep, ok = verify_run(out(climb=dim(5, 4, 7, ids=("fact:x:made_up",))), KNOWN, VALUES)
    assert not ok and not rep["climb"]["valid"] and rep["walking"]["valid"]
    assert rep["climb"]["invalid_ids"] == ["fact:x:made_up"]


def test_conditions_required_and_order():
    rep, _ = verify_run(out(heat=dim(5, 3, 5, lc=[])), KNOWN, VALUES)
    assert "lower_conditions missing" in rep["heat"]["reason"]
    rep, _ = verify_run(out(heat=dim(5, 6, 7)), KNOWN, VALUES)
    assert "violated" in rep["heat"]["reason"]


def test_numeric_spot_check():
    o = out()
    o["numeric_claims"] = [{"evidence_id": "fact:x:steps_count", "value": 400}]
    rep, ok = verify_run(o, KNOWN, VALUES)
    assert not ok and rep["climb"]["numeric_fail"][0]["actual"] == 156
    o["numeric_claims"] = [{"evidence_id": "fact:x:steps_count", "value": 156}]
    assert verify_run(o, KNOWN, VALUES)[1]


def test_web_citation_by_url_or_id():
    url = "https://example.com/a"
    known = KNOWN | {web_id(url)}
    for cid in (url, web_id(url), "web:" + url):
        rep, ok = verify_run(out(crowd=dim(5, 4, 7, ids=(cid,))), known, VALUES, {url: web_id(url)})
        assert ok, cid


def test_aggregate_median_and_spread():
    runs = [{"output": out(climb=dim(t, 4, 9)), "report": verify_run(out(climb=dim(t, 4, 9)), KNOWN, VALUES)[0]}
            for t in (5, 6, 9)]
    agg = aggregate(runs)
    assert agg["dimensions"]["climb"]["typical"] == 6
    assert agg["status"] == "needs_review" and any("climb.typical" in f for f in agg["flags"])
    ok = aggregate(runs[:2])
    assert ok["status"] == "ok" and ok["grade_display"]["typical"] == "중"


def test_aggregate_invalid_run_excluded():
    bad = out(climb=dim(5, 4, 7, ids=("nope",)))
    runs = [{"output": bad, "report": verify_run(bad, KNOWN, VALUES)[0]}]
    agg = aggregate(runs)
    assert agg["dimensions"]["climb"]["typical"] is None and agg["composite"]["typical"] is None
    assert agg["status"] == "needs_review"
