"""Judge API cost from recorded usage: python -m src.scoring.cost_report [--rubric v2.2] [--since 2026-11-03T13:00]

Prices: Claude API list prices for claude-sonnet-5-5 (claude-api skill, cached 2026-10-06).
Re-check https://platform.claude.com/docs/en/about-claude/pricing before quoting externally.
SerpApi (google_web_search) is billed by SerpApi plan, so it is counted, not priced.
"""
import argparse

from . import db

PRICE = {  # USD per 1M tokens
    "input_tokens": 2.00,
    "cache_creation_input_tokens": 2.50,  # 5-minute TTL write = 1.25x input
    "cache_read_input_tokens": 0.20,
    "output_tokens": 10.00,
}
WEB_SEARCH_PER_1K = 10.00  # Anthropic server-side web_search


def run_cost(u):
    tok = sum(PRICE[k] * (u.get(k) or 0) for k in PRICE) / 1e6
    return tok + WEB_SEARCH_PER_1K * (u.get("web_search_requests") or 0) / 1000


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubric", default="v2.2")
    ap.add_argument("--since", help="only runs created at/after this ISO time (UTC)")
    a = ap.parse_args(argv)
    sql = "select run_id, place_id, created_at, usage from scoring_judgments where rubric_version=%s"
    params = [a.rubric]
    if a.since:
        sql += " and created_at >= %s"
        params.append(a.since)
    with db.connect() as conn:
        rows = db.query(conn, sql + " order by created_at", params)
    per_site, tot = {}, {k: 0 for k in [*PRICE, "web_search_requests"]}
    for r in rows:
        u = r["usage"] or {}
        for k in tot:
            tot[k] += u.get(k) or 0
        s = per_site.setdefault(r["place_id"], {"runs": 0, "usd": 0.0})
        s["runs"] += 1
        s["usd"] += run_cost(u)
    total = sum(s["usd"] for s in per_site.values())
    print(f"rubric={a.rubric} runs={len(rows)} sites={len(per_site)}")
    for k, v in tot.items():
        print(f"  {k}: {v:,}")
    for pid, s in sorted(per_site.items()):
        print(f"  {pid}: runs={s['runs']} ${s['usd']:.3f}")
    if per_site:
        print(f"TOTAL ${total:.2f} · per site ${total / len(per_site):.3f} · per run ${total / len(rows):.3f}")


if __name__ == "__main__":
    main()
