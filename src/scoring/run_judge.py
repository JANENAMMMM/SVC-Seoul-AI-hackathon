"""CLI: python -m src.scoring.run_judge --sites dad-02,dad-03 --runs 1"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .judge import RUBRIC_VERSION, cache_web, judge
from .provenance import explanations
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--runs", type=int, default=1)
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
            runs = []
            for k in range(1, a.runs + 1):
                res = judge(site, conn, run_index=k)
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
                (OUT_DIR / f"{site}_run{k}.json").write_text(db.dumps(res), encoding="utf-8")
                runs.append({"run_index": k, "run_id": run_id,
                             "output": res["output"], "report": report})
                print(site, f"run{k}", "tool_calls", res["tool_calls"], "usage", res["usage"], "valid", ok)
            agg = aggregate(runs)
            source = explanations(agg, runs)
            agg["conditions"] = {d: {k: source[d][k] for k in ("lower_conditions", "upper_conditions")}
                                 for d in source}
            agg["explanation_sources"] = source
            agg["representative_route"] = source["climb"]["route"]
            c = agg["composite"]
            db.upsert(conn, "scoring_scores", [dict(
                place_id=site, rubric_version=RUBRIC_VERSION, dimensions=agg["dimensions"],
                composite_typical=c["typical"], composite_lower=c["lower"], composite_upper=c["upper"],
                grade_display=agg["grade_display"]["typical"], confidence=agg["confidence"],
                status=agg["status"], conditions_json={"conditions": agg["conditions"], "flags": agg["flags"],
                                                       "route": agg["representative_route"],
                                                       "explanation_sources": source},
                updated_at=datetime.now(timezone.utc))], key=("place_id", "rubric_version"))
            all_scores[site] = agg
            print(site, "composite", c, agg["grade_display"], agg["status"], agg["flags"])
    merged = json.loads(SCORES.read_text(encoding="utf-8")) if SCORES.exists() else {}
    if not isinstance(merged, dict):
        merged = {}
    merged.update(json.loads(db.dumps(all_scores)))  # keep sites from earlier batches
    SCORES.write_text(db.dumps(merged), encoding="utf-8")


if __name__ == "__main__":
    main()
