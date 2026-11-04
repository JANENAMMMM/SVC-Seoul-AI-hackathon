"""Verification + aggregation for v2 judge outputs (pure functions, no I/O)."""
import json
import hashlib
import math
import statistics

DIMS = ("climb", "walking", "heat", "crowd")
WEIGHTS = {"climb": 3, "walking": 3, "heat": 2, "crowd": 1}
LEVELS = ("typical", "lower", "upper")


def web_id(url):
    return "web:" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def round_half_up(x):
    return int(math.floor(x + 0.5))


def grade_display(score):
    if score is None:
        return None
    return "하" if score <= 3 else "중" if score <= 6 else "상"


def composite(dims):
    """dims: {dim: {typical, lower, upper}} -> {typical, lower, upper} weighted, rounded."""
    out = {}
    for lv in LEVELS:
        if any(dims.get(d, {}).get(lv) is None for d in DIMS):
            out[lv] = None
            continue
        tot = sum(WEIGHTS[d] * dims[d][lv] for d in DIMS)
        out[lv] = round_half_up(tot / sum(WEIGHTS.values()))
    return out


def _ids(dim_out):
    ids = list(dim_out.get("evidence_ids") or [])
    for key in ("lower_conditions", "upper_conditions"):
        for c in dim_out.get(key) or []:
            ids += c.get("evidence_ids") or []
    return ids


def resolve(cid, known_ids, web_urls):
    """known_ids: set of evidence/review/web ids; web_urls: {url: web_id}."""
    if cid in known_ids:
        return True
    if cid.startswith("web:http"):
        cid = cid[4:]
    if cid.startswith("http"):
        if cid in web_urls or web_id(cid) in known_ids:
            return True
        norm = _norm_url(cid)  # tolerate www./scheme/trailing-slash differences
        return any(_norm_url(u) == norm for u in web_urls)
    return False


def _norm_url(u):
    u = u.strip().lower().split("#")[0]
    for p in ("https://", "http://"):
        if u.startswith(p):
            u = u[len(p):]
    if u.startswith("www."):
        u = u[4:]
    return u.rstrip("/")


def check_numeric(claims, values, rel_tol=0.05):
    """claims: [{evidence_id, value}], values: {id: value}. Returns list of failures."""
    bad = []
    for c in claims or []:
        eid, v = c.get("evidence_id"), c.get("value")
        src = values.get(eid)
        if not isinstance(src, (int, float)) or isinstance(src, bool) or not isinstance(v, (int, float)):
            continue  # only spot-check numeric evidence
        if abs(src - v) > max(rel_tol * abs(src), 0.01):
            bad.append({"evidence_id": eid, "claimed": v, "actual": src})
    return bad


def verify_run(output, known_ids, values, web_urls=None):
    """Returns {dim: {valid, invalid_ids, numeric_fail, reason}} and overall flag."""
    web_urls = web_urls or {}
    report = {}
    if isinstance(output, str):  # model occasionally returns the JSON as a string
        try:
            output = json.loads(output)
        except ValueError:
            output = {}
    if not isinstance(output, dict):
        output = {}
    dims_out = output.get("dimensions")
    if isinstance(dims_out, str):
        try:
            output["dimensions"] = json.loads(dims_out)
        except ValueError:
            output["dimensions"] = {}
    claims = output.get("numeric_claims") or []
    if isinstance(claims, str):
        try:
            claims = json.loads(claims)
        except ValueError:
            claims = []
    for d in DIMS:
        dout = (output.get("dimensions") or {}).get(d)
        if not dout:
            report[d] = {"valid": False, "reason": "missing"}
            continue
        reasons = []
        scores = [dout.get(lv) for lv in LEVELS]
        if any(not isinstance(s, int) or not 1 <= s <= 10 for s in scores):
            reasons.append("score out of range")
        elif not dout["lower"] <= dout["typical"] <= dout["upper"]:
            reasons.append("lower<=typical<=upper violated")
        for key, lv in (("lower_conditions", "lower"), ("upper_conditions", "upper")):
            conds = dout.get(key) or []
            if dout.get(lv) != dout.get("typical") and not conds:
                reasons.append(f"{key} missing")
            if any(not c.get("evidence_ids") for c in conds):
                reasons.append(f"{key} without evidence")
        ids = _ids(dout)
        if not ids:
            reasons.append("no citations")
        invalid = [i for i in dict.fromkeys(ids) if not resolve(i, known_ids, web_urls)]
        if invalid:
            reasons.append("invalid citations")
        dim_ids = set(ids)
        nfail = check_numeric([c for c in claims if c.get("evidence_id") in dim_ids], values)
        if nfail:
            reasons.append("numeric mismatch")
        report[d] = {"valid": not reasons, "invalid_ids": invalid, "numeric_fail": nfail,
                     "reason": "; ".join(reasons) or None}
    return report, all(r["valid"] for r in report.values())


def aggregate(runs):
    """runs: [{output, report}] -> score record (median over valid runs per dimension)."""
    dims, flags, notes = {}, [], []
    for d in DIMS:
        vals = [r["output"]["dimensions"][d] for r in runs if r["report"].get(d, {}).get("valid")]
        if not vals:
            dims[d] = {lv: None for lv in LEVELS}
            flags.append(f"{d}: no valid run")
            continue
        # medoid: the valid run closest to the per-level median, so every published score is exactly
        # one run's output (provenance needs an exact match; a 2-run median can fall between runs)
        med = {lv: statistics.median(v[lv] for v in vals) for lv in LEVELS}
        best = min(vals, key=lambda v: sum(abs(v[lv] - med[lv]) for lv in LEVELS))
        dims[d] = {lv: best[lv] for lv in LEVELS}
        for lv in LEVELS:
            spread = max(v[lv] for v in vals) - min(v[lv] for v in vals)
            if spread > 2:
                flags.append(f"{d}.{lv}: spread {spread} > 2")
        if len(vals) < len(runs):
            msg = f"{d}: {len(runs) - len(vals)} invalid run(s)"
            agree = len(vals) >= 2 and all(
                max(v[lv] for v in vals) - min(v[lv] for v in vals) <= 1 for lv in LEVELS)
            # v2.2: an invalid run is only a review trigger if the remaining valid runs can't vouch
            # for the score (fewer than 2, or they disagree by more than 1 point)
            (notes if agree else flags).append(msg)
    comp = composite(dims)
    confs = [r["output"].get("confidence") for r in runs if r["output"].get("confidence")]
    order = {"low": 0, "medium": 1, "high": 2}
    conf = min(confs, key=lambda c: order.get(c, 0)) if confs else "low"
    return {
        "dimensions": dims,
        "composite": comp,
        "grade_display": {lv: grade_display(comp[lv]) for lv in LEVELS},
        "confidence": conf,
        "status": "needs_review" if flags else "ok",
        "flags": flags,
        "notes": notes,  # invalid runs outvoted by >=2 agreeing valid runs (not a review trigger)
        "n_runs": len(runs),
    }
