"""CLI: python -m src.scoring.run_judge --sites dad-02,dad-03 --runs 1"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .judge import RUBRIC_VERSION, cache_web, judge
from .provenance import explanations, snapshot_runs
from .verify import aggregate, verify_run

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data/scoring/judge/v2"
SCORES = ROOT / "data/scoring/scores_v2.json"


def known(conn):
    # v2.2: fact:* (initial site facts) are hidden from the judge, so citing them is invalid
    ids = {r["id"] for r in db.query(conn, "select id from scoring_evidence where id not like 'fact:%%'")}
    ids |= {r["id"] for r in db.query(conn, "select id from scoring_reviews")}
    web = db.query(conn, "select id, url from scoring_web_cache")
    ids |= {r["id"] for r in web}
    values = {r["id"]: r["value"] for r in db.query(conn, "select id, value from scoring_evidence where id not like 'fact:%%'")}
    return ids, values, {r["url"]: r["id"] for r in web}


def enough(runs):
    """Adaptive repeat: stop early when the runs so far are already stable.

    - 1 run is enough if every dimension passed verification and confidence is not low.
    - 2 runs are enough if both are fully valid and every dimension's typical/lower/upper differ by <= 1.
    Otherwise run again (up to --runs).
    """
    if not runs:
        return False
    def ok(r):
        return all(v.get("valid") for v in r["report"].values())
    if len(runs) == 1:
        r = runs[0]
        return ok(r) and (r["output"].get("confidence") or "low") != "low"
    if len(runs) == 2 and all(ok(r) for r in runs):
        d0, d1 = (r["output"]["dimensions"] for r in runs)
        return all(abs(d0[d][lv] - d1[d][lv]) <= 1 for d in d0 for lv in ("typical", "lower", "upper"))
    return False


def judge_site(conn, site, max_runs=3, fixed=False, out_dir=OUT_DIR, judge_fn=None):
    """Run the judge for one site (adaptive repeats) and save run files to out_dir. Does not publish."""
    judge_fn = judge_fn or judge
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{site}_run*.json"):  # adaptive runs may be fewer than before
        old.unlink()
    runs = []
    for k in range(1, max_runs + 1):
        if not fixed and enough(runs):
            break
        res = judge_fn(site, conn, run_index=k)
        if isinstance(res.get("output"), str):  # normalize stringified JSON output
            try:
                res["output"] = json.loads(res["output"])
            except ValueError:
                res["output"] = {}
        cache_web(conn, res)
        ids, values, web_urls = known(conn)
        report, ok = verify_run(res["output"], ids, values, web_urls)
        res["verify"] = report
        res["citations_valid"] = ok
        run_id = f"{site}:{RUBRIC_VERSION}:{datetime.now(timezone.utc):%Y%m%dT%H%M%S}:r{k}"
        res["run_id"] = run_id
        db.upsert(conn, "scoring_judgments", [dict(
            run_id=run_id, place_id=site, model=res["model"], rubric_version=RUBRIC_VERSION,
            run_index=k, output_json=res["output"], citations_valid=ok,
            usage={**res["usage"], "tool_calls": res["tool_calls"], "verify": report})], key=("run_id",))
        (out_dir / f"{site}_run{k}.json").write_text(db.dumps(res), encoding="utf-8")
        runs.append({"run_index": k, "run_id": run_id, "output": res["output"], "report": report,
                     "usage": res["usage"]})
        print(site, f"run{k}", "tool_calls", res["tool_calls"], "usage", res["usage"], "valid", ok)
    return runs


def aggregate_site(conn, site, runs):
    """Aggregate runs into the published score shape (no writes)."""
    agg = aggregate(runs)
    place = db.query(conn, "select name_ko from scoring_places where id=%s", (site,))
    agg = {"name_ko": place[0]["name_ko"] if place else site, **agg}  # needed by visit_modes.build_modes
    source = explanations(agg, runs)
    agg["conditions"] = {d: {k: source[d][k] for k in ("lower_conditions", "upper_conditions")}
                         for d in source}
    agg["explanation_sources"] = source
    agg["representative_route"] = source["climb"]["route"]
    return agg


def publish_site(conn, site, agg, scores_path=SCORES):
    """Write one site's aggregated score to scoring_scores and the scores JSON."""
    c = agg["composite"]
    source = agg["explanation_sources"]
    db.upsert(conn, "scoring_scores", [dict(
        place_id=site, rubric_version=RUBRIC_VERSION, dimensions=agg["dimensions"],
        composite_typical=c["typical"], composite_lower=c["lower"], composite_upper=c["upper"],
        grade_display=agg["grade_display"]["typical"], confidence=agg["confidence"],
        status=agg["status"], conditions_json={"conditions": agg["conditions"], "flags": agg["flags"],
                                               "route": agg["representative_route"],
                                               "explanation_sources": source},
        updated_at=datetime.now(timezone.utc))], key=("place_id", "rubric_version"))
    scores_path = Path(scores_path)
    merged = json.loads(scores_path.read_text(encoding="utf-8")) if scores_path.exists() else {}
    if not isinstance(merged, dict):
        merged = {}
    merged[site] = json.loads(db.dumps(agg))  # keep other sites
    scores_path.write_text(db.dumps(merged), encoding="utf-8")
    print(site, "composite", c, agg["grade_display"], agg["status"], agg["flags"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--runs", type=int, default=3, help="maximum runs per site")
    ap.add_argument("--fixed", action="store_true", help="always do --runs runs (no early stop)")
    ap.add_argument("--reaggregate", action="store_true",
                    help="no API calls: rebuild published scores from saved run files (after a rule change)")
    ap.add_argument("--replace", action="store_true", help="explicitly replace an existing site's published score")
    a = ap.parse_args(argv)
    sites = [s.strip() for s in a.sites.split(",") if s.strip()]
    if a.runs < 1 or not sites:
        ap.error("provide sites and --runs >= 1")
    all_scores = json.loads(SCORES.read_text(encoding="utf-8")) if SCORES.exists() else {}
    existing = [site for site in sites if site in all_scores]
    if existing and not a.replace:
        ap.error(f"published scores exist for {', '.join(existing)}; --replace required")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with db.connect() as conn:
        db.ensure_schema(conn)
        for site in sites:
            if a.reaggregate:
                runs = snapshot_runs(site, OUT_DIR)
                if not runs:
                    raise SystemExit(f"no saved runs for {site}")
            else:
                runs = judge_site(conn, site, a.runs, a.fixed)
            publish_site(conn, site, aggregate_site(conn, site, runs))


if __name__ == "__main__":
    main()
