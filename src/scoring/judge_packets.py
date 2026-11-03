"""LLM-as-a-judge 검증용 근거 묶음 생성.

규칙 엔진의 수준·등급은 빼고, 원 근거(측정값·공식 사실·리뷰 인용)만 관광지별로 묶는다.
judge는 이 묶음만 보고 독립적으로 채점 → 규칙 엔진 결과와 일치도를 비교한다.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "scoring"


def _read(rel, default):
    p = ROOT / rel
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def build():
    features = _read("features.json", [])
    facts = _read("derived/site_facts.json", {})
    facts_by_id = {}
    for v in (facts.values() if isinstance(facts, dict) else facts):
        if isinstance(v, dict) and v.get("id"):
            facts_by_id[v["id"]] = v
    reviews = _read("derived/review_signals_tripadvisor.json", {})
    rev_sites = reviews.get("attractions", {}) if isinstance(reviews, dict) else {}
    packets = []
    for s in features:
        sid = s["id"]
        ev = []
        for dim, items in s["dimensions"].items():
            for it in items:
                ev.append({"metric": it["metric"], "value": it["value"], "unit": it["unit"],
                           "source": it["source"], "note": it.get("note", "")})
        fact = facts_by_id.get(sid, {})
        quotes = []
        r = rev_sites.get(sid, {}) if isinstance(rev_sites, dict) else {}
        for dim, d in (r.get("dims") or {}).items():
            for t in (d.get("evidence") or [])[:2]:
                quotes.append({"dimension": dim, "quote": t if isinstance(t, str) else t.get("text", str(t))})
        packets.append({"id": sid, "name_ko": s["name_ko"], "measurements": ev,
                        "official_facts": {k: v for k, v in fact.items() if k not in ("id",)},
                        "review_quotes": quotes})
    out = ROOT / "judge" / "packets.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(packets, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
