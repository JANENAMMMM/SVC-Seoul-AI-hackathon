"""Migrate collected scoring data into scoring_* tables (stable string IDs)."""
import json
import re
from pathlib import Path

from . import db

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/scoring"


def read(name, default):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def slug(s):
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "_", str(s)).strip("_").lower()[:60]


FACT_DIM = {
    "steps_count": "climb", "steps_note": "climb", "steps_unavoidable": "climb", "elevator": "climb",
    "elevator_note": "climb", "trail_gain_m": "climb", "trail_gain_note": "climb", "cable_car": "climb",
    "summit_elevation_m": "climb", "golden_bridge_elevation_m": "climb", "floors": "climb",
    "floor_note": "climb", "statue_height_m": "climb", "sun_wheel_height_m": "climb",
    "internal_route_km": "walking", "internal_route_note": "walking", "site_area_ha": "walking",
    "area_note": "walking", "route_length_km": "walking", "route_note": "walking",
    "golden_bridge_length_m": "walking", "surface": "walking", "boat_duration_min": "walking",
    "exposure": "heat", "heat_note": "heat", "air_conditioned": "heat", "night": "heat",
    "night_show": "crowd", "vehicle_free_hours": "crowd",
}
SKIP_FACT = {"id", "sources", "source_url", "steps_source_type"}
UNITS = {"_km": "km", "_m": "m", "_ha": "ha", "_min": "min", "steps_count": "steps"}


def unit_for(k):
    for suf, u in UNITS.items():
        if k.endswith(suf):
            return u
    return None


REV_DIM = {"walking": "walking", "stairs_climb": "climb", "heat_sun": "heat", "queue_crowd": "crowd",
           "rest_seating": "general", "surface": "walking", "accessibility_elderly": "general",
           "relief": "climb"}
REV_CAVEAT = {"stairs_climb": "regex 매칭, 수동 점검 정밀도 약 90%",
              "queue_crowd": "regex 매칭, 수동 점검 정밀도 약 70% (line/wait 오탐)",
              "heat_sun": "regex 매칭; 온천 등 'hot' 오탐 가능"}
TOPIC_DIM = [(r"stair|step|climb|steep|hik", "climb"), (r"walk", "walking"),
             (r"hot|heat|sun|shade|humid", "heat"), (r"crowd|queue|line|wait|busy", "crowd"),
             (r"elevator|cable|lift|shuttle|buggy|cart", "climb"), (r"계단|오르", "climb"),
             (r"걷|도보", "walking"), (r"더위|덥|햇", "heat"), (r"사람|붐|대기|줄", "crowd")]


def topic_dim(k):
    for pat, d in TOPIC_DIM:
        if re.search(pat, k, re.I):
            return d
    return "general"


def build():
    sites = read("attractions.json", [])
    facts = {v["id"]: v for v in read("derived/site_facts.json", {}).values()}
    gps = {s["id"]: s for s in read("derived/gps_traces.json", {}).get("sites", [])}
    revsig = read("derived/review_signals_tripadvisor.json", {}).get("attractions", {})
    gtopics = read("raw/google_topics.json", {})
    osm = {o["id"]: o for o in read("derived/osm_features.json", [])}
    climate = read("derived/climate_danang.json", {})
    places, ev, reviews = [], [], []

    def add(id_, pid, dim, basis, metric, value, unit, text, source, url=None, caveat=None):
        ev.append(dict(id=id_, place_id=pid, dimension=dim, basis=basis, metric=metric, value=value,
                       unit=unit, text=text, source=source, source_url=url, caveat=caveat))

    for s in sites:
        sid = s["id"]
        g = s.get("google") or {}
        places.append(dict(id=sid, name_ko=s.get("name_ko"), name_en=s.get("name_en"), lat=s.get("lat"),
                           lng=s.get("lng"), google_place_id=g.get("place_id"),
                           tripadvisor_url=(revsig.get(sid) or {}).get("url"),
                           meta={"google_types": g.get("type"), "hours": g.get("hours"),
                                 "google_rating": g.get("rating"), "google_reviews": g.get("reviews"),
                                 "extensions": g.get("extensions"), "address": g.get("address")}))
        # facts
        f = facts.get(sid, {})
        urls = f.get("source_url") or [x.get("url") for x in f.get("sources", []) if isinstance(x, dict)]
        url = urls[0] if isinstance(urls, list) and urls else urls if isinstance(urls, str) else None
        stype = f.get("steps_source_type") or ", ".join(
            f"{x.get('type')}({x.get('confidence')})" for x in f.get("sources", []) if isinstance(x, dict))
        for k, v in f.items():
            if k in SKIP_FACT or v is None:
                continue
            txt = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            add(f"fact:{sid}:{k}", sid, FACT_DIM.get(k, "general"), "B", k, v, unit_for(k),
                f"{k} = {txt}", "site_facts (web 조사)", url,
                f"출처 유형: {stype}" + ("; 출처 URL: " + " | ".join(urls) if isinstance(urls, list) else ""))
        # gps
        gs = gps.get(sid)
        if gs:
            sm = gs["summary"]
            n = sm.get("n_traces", 0)
            cav = (f"OSM 공개 GPS 궤적 n={n}, coverage={sm.get('coverage')}; zone={gs['zone']['source']}"
                   + ("; 표본 부족" if n < 5 else ""))
            for m, unit, dim in [("median_km", "km", "walking"), ("p25_km", "km", "walking"),
                                 ("p75_km", "km", "walking"), ("median_duration_min", "min", "walking"),
                                 ("median_ascent_m", "m", "climb"), ("median_speed_mps", "m/s", "walking")]:
                if sm.get(m) is not None:
                    add(f"gps:{sid}:{m}", sid, dim, "B" if n >= 5 else "C", m, sm[m], unit,
                        f"GPS 궤적 {m} = {sm[m]} {unit} (n={n})", "OSM trackpoints + Open-Meteo elevation",
                        "https://api.openstreetmap.org/api/0.6/trackpoints", cav)
        # osm
        o = osm.get(sid)
        if o:
            cav = "300m buffer, not site boundary; OSM 태그 커버리지 낮음"
            el = o.get("elevation") or {}
            for m, val, unit, dim in [
                ("pedestrian_length_m", o.get("pedestrian_length_m"), "m", "walking"),
                ("steps_count", o.get("steps_count"), "ways", "climb"),
                ("steps_length_m", o.get("steps_length_m"), "m", "climb"),
                ("step_count_sum", o.get("step_count_sum"), "steps", "climb"),
                ("elevator_count", o.get("elevator_count"), "count", "climb"),
                ("aerialway", o.get("aerialway"), None, "climb"),
                ("bench_count", o.get("bench_count"), "count", "general"),
                ("toilets_count", o.get("toilets_count"), "count", "general"),
                ("elevation_range_m", el.get("range_m"), "m", "climb"),
                ("walk_only_climb_m", el.get("walk_only_climb_m"), "m", "climb"),
            ]:
                if val is not None:
                    add(f"osm:{sid}:{m}", sid, dim, "C", m, val, unit,
                        f"OSM {m} = {val}{' ' + unit if unit else ''} (매칭: {o.get('osm_name')})",
                        "OpenStreetMap Overpass", f"https://www.openstreetmap.org/{o.get('osm_type')}/{o.get('osm_id')}",
                        cav + ("; step_count 태그 일부 계단만" if m == "step_count_sum" else ""))
        # tripadvisor regex signals
        rs = revsig.get(sid)
        if rs:
            for dk, d in rs["dims"].items():
                add(f"rev:{sid}:sig_{dk}", sid, REV_DIM.get(dk, "general"), "C", f"review_share_{dk}",
                    d.get("share"), "share",
                    f"Tripadvisor 리뷰 {rs['n']}건 중 {dk} 언급 {d.get('hits')}건 (비율 {d.get('share')}, 95%CI {d.get('ci95')}; 가족 {d.get('family_hits')}/{rs.get('n_family')})",
                    "Tripadvisor (Apify)", rs.get("url"), REV_CAVEAT.get(dk, "regex 매칭, 정밀도 미검증"))
        # google topics
        gt = gtopics.get(sid) or {}
        tot = gt.get("total_reviews")
        for lang in ("en", "ko"):
            for t in gt.get(f"topics_{lang}") or []:
                kw = t.get("keyword")
                if not kw:
                    continue
                cav = f"Google 토픽 언급 수/전체 리뷰 {tot}건; 토픽은 Google 자동 추출"
                if re.search(r"\bhot\b", kw, re.I) or "spring" in kw.lower():
                    cav += "; 온천(hot spring) 'hot'은 더위 아님(오탐)"
                add(f"topic:{sid}:{slug(kw)}", sid, topic_dim(kw), "C", "google_topic_mentions",
                    t.get("mentions"), "mentions", f"Google 리뷰 토픽 '{kw}' 언급 {t.get('mentions')}회 ({lang})",
                    "Google Maps (SerpApi)", None, cav)
            for i, r in enumerate(gt.get(f"reviews_{lang}") or [], 1):
                if r.get("snippet"):
                    reviews.append(dict(id=f"rev:{sid}:g{lang}{i}", place_id=sid, source="google", lang=lang,
                                        date=r.get("date"), trip_type=None, rating=r.get("rating"),
                                        text=r["snippet"]))
        # tripadvisor raw reviews
        tp = DATA / "raw/tripadvisor" / f"{sid}.json"
        if tp.exists():
            for i, r in enumerate(json.loads(tp.read_text(encoding="utf-8")).get("reviews", []), 1):
                text = ((r.get("title") or "") + "\n" + (r.get("text") or "")).strip()
                reviews.append(dict(id=f"rev:{sid}:{i}", place_id=sid, source="tripadvisor", lang=r.get("lang"),
                                    date=r.get("travelDate") or r.get("publishedDate"), trip_type=r.get("tripType"),
                                    rating=r.get("rating"), text=text))
    for m, v in (climate.get("monthly_mean_apparent_max_c") or {}).items():
        add(f"climate:{m}", None, "heat", "A", "monthly_mean_apparent_max_c", v, "°C",
            f"다낭 {m}월 일 최고 체감온도 평균 {v}°C ({climate.get('period')})", "Open-Meteo archive",
            climate.get("source"), "다낭 시내 격자점 기준; 산지(바나힐 등)는 더 낮음")
    # de-dup ids (keep first)
    seen, ev2 = set(), []
    for e in ev:
        if e["id"] not in seen:
            seen.add(e["id"])
            ev2.append(e)
    return places, ev2, reviews


def main():
    places, ev, reviews = build()
    with db.connect() as conn:
        print("public tables (before):", db.list_public_tables(conn))
        db.ensure_schema(conn)
        db.upsert(conn, "scoring_places", places)
        db.upsert(conn, "scoring_evidence", ev)
        db.upsert(conn, "scoring_reviews", reviews)
        for t in ("scoring_places", "scoring_evidence", "scoring_reviews", "scoring_web_cache",
                  "scoring_judgments", "scoring_scores"):
            print(t, db.count(conn, t))


if __name__ == "__main__":
    main()
