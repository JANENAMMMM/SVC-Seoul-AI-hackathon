"""Normalize evidence from the collected scoring sources."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/scoring"


def read(name, default):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def item(basis, metric, value, unit, source, note=""):
    return dict(basis=basis, metric=metric, value=value, unit=unit, source=source, note=note)


def build_features(write=True):
    sites = read("attractions.json", [])
    facts = {v["id"]: v for v in read("derived/site_facts.json", {}).values()}
    gps = {v["id"]: v["summary"] for v in read("derived/gps_traces.json", {}).get("sites", [])}
    reviews = read("derived/review_signals_tripadvisor.json", {}).get("attractions", {})
    topics = read("derived/google_topic_signals.json", {})
    osm = {v["id"]: v for v in read("derived/osm_features.json", [])}
    out = []
    for site in sites:
        sid = site["id"]
        f, g, r, t, o = (source.get(sid, {}) for source in (facts, gps, reviews, topics, osm))
        dims = {f"D{i}": [] for i in range(1, 6)}
        add = lambda d, *args: dims[d].append(item(*args))
        if g.get("coverage") == "usable" and g.get("n_traces", 0) >= 5:
            for d, key, unit in (("D1", "median_km", "km"), ("D2", "median_ascent_m", "m")):
                if g.get(key) is not None:
                    add(d, "A", key, g[key], unit, "gps_traces", f"n={g['n_traces']}; usable")
        elif g.get("n_traces", 0) >= 2:  # weak GPS (2~4 traces): measured behavior, but downgraded to B
            for d, key, unit in (("D1", "median_km", "km"), ("D2", "median_ascent_m", "m")):
                if g.get(key) is not None:
                    add(d, "B", key, g[key], unit, "gps_traces", f"n={g['n_traces']}; weak")
        if o:
            if o.get("pedestrian_length_m") is not None:
                add("D1", "B", "pedestrian_length_km", o["pedestrian_length_m"] / 1000, "km", "osm_features", o.get("zone_type", ""))
            climb = o.get("elevation", {}).get("walk_only_climb_m")
            if climb is not None:
                add("D2", "B", "walk_only_climb_m", climb, "m", "osm_features", o["elevation"].get("walk_only_method", ""))
            if o.get("step_count_sum") is not None:
                add("D2", "B", "step_count_sum", o["step_count_sum"], "steps", "osm_features", "mapped steps only")
        if f.get("internal_route_km") is not None and "GPS trace 1개" not in f.get("internal_route_note", ""):
            add("D1", "B", "internal_route_km", f["internal_route_km"], "km", "site_facts", f.get("internal_route_note", ""))
        if f.get("trail_gain_m") is not None:
            add("D2", "B", "trail_gain_m", f["trail_gain_m"], "m", "site_facts", f.get("trail_gain_note", ""))
        if f.get("steps_count") is not None:
            add("D2", "B", "steps_count", f["steps_count"], "steps", "site_facts", f.get("steps_note", ""))
        transport = bool(f.get("cable_car") or f.get("elevator") or f.get("shuttle") or f.get("electric_cart") or o.get("aerialway") or o.get("elevator_count") or o.get("rail_shuttle"))
        if transport or f.get("steps_unavoidable") is not None:
            full = bool(f.get("cable_car") or o.get("aerialway")) and not f.get("steps_unavoidable")
            add("D3", "B", "transport_available", transport, "bool", "site_facts" if f else "osm_features", "major_climb_replaced" if full else "partial_or_no_relief")
        exposure = str(f.get("exposure", "")).lower()
        if exposure:
            outdoor = not exposure.startswith("indoor") and not exposure.startswith("실내")
            add("D4", "B", "outdoor", outdoor, "bool", "site_facts", exposure)
        if r.get("n", 0) >= 100:
            mapping = {"D1": "walking", "D2": "stairs_climb", "D3": "relief", "D4": "heat_sun", "D5": "queue_crowd"}
            for d, key in mapping.items():
                signal = r.get("dims", {}).get(key, {})
                if signal.get("share") is not None:
                    note = f"n={r['n']}; Wilson CI={signal.get('ci95')}"
                    if d == "D4" and sid == "dad-11":
                        note += "; hot spring/hot water false-positive risk"
                        continue
                    add(d, "C", key + "_share", signal["share"], "ratio", "review_signals_tripadvisor", note)
        for d, group, key in (("D2", "burden", "stairs"), ("D3", "relief", "transport"), ("D5", "burden", "crowd")):
            signal = t.get(group, {}).get(key, {})
            if signal.get("ratio") is not None:
                add(d, "C", "google_" + key + "_ratio", signal["ratio"], "ratio", "google_topic_signals", "topic mentions / all Google reviews; sparse topic index")
        out.append({"id": sid, "name_ko": site["name_ko"], "dimensions": dims})
    if write:
        (DATA / "features.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
