"""OSM public GPS traces -> on-foot walking metrics per attraction.

Usage: python src/scoring/collect/gps_traces.py
Output: data/scoring/derived/gps_traces.json
"""
import json, math, os, statistics, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA = os.path.join(ROOT, "data", "scoring")
OUT = os.path.join(DATA, "derived", "gps_traces.json")
UA = "bangeoreum-research/0.1 (hackathon)"
NS = "{http://www.topografix.com/GPX/1/0}"
HALF_M = {"dad-01": 1500, "dad-12": 800, "dad-03": 600, "dad-13": 1500}
DEFAULT_HALF = 400
MAX_PAGES = 15
_last = [0.0]


def get(url):
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                _last[0] = time.time()
                return r.read()
        except Exception as e:  # noqa
            _last[0] = time.time()
            if attempt == 4:
                raise
            time.sleep(65 if getattr(e, "code", None) == 429 else 3)


def hav(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def load_sites():
    seed = json.load(open(os.path.join(DATA, "attractions_seed.json"), encoding="utf-8"))
    coords = {}
    p = os.path.join(DATA, "attractions.json")
    if os.path.exists(p):
        for a in json.load(open(p, encoding="utf-8")):
            if a.get("lat") is not None:
                coords[a["id"]] = (a["lat"], a["lng"])
    for s in seed:
        if s["id"] not in coords:
            q = urllib.parse.quote(s["query"])
            r = json.loads(get(f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}"))
            if r:
                coords[s["id"]] = (float(r[0]["lat"]), float(r[0]["lon"]))
        s["lat"], s["lng"] = coords.get(s["id"], (None, None))
    return seed


def load_osm():
    p = os.path.join(DATA, "derived", "osm_features.json")
    if not os.path.exists(p):
        return {}
    d = json.load(open(p, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("sites", d)
    out = {}
    if isinstance(items, dict):
        items = [dict(v, id=k) if isinstance(v, dict) else {} for k, v in items.items()]
    for it in items:
        if isinstance(it, dict) and it.get("id"):
            out[it["id"]] = it
    return out


def zone_for(site, osm):
    f = osm.get(site["id"], {})
    bb = f.get("bbox")
    if isinstance(bb, (list, tuple)) and len(bb) == 4:
        # assume [minlon, minlat, maxlon, maxlat]
        return tuple(bb), "osm_bbox"
    half = HALF_M.get(site["id"], DEFAULT_HALF)
    dlat = half / 111320.0
    dlon = half / (111320.0 * math.cos(math.radians(site["lat"])))
    return (site["lng"] - dlon, site["lat"] - dlat, site["lng"] + dlon, site["lat"] + dlat), f"point_bbox_{half}m"


def aerial_lines(site, osm):
    f = osm.get(site["id"], {})
    lines = []
    for a in f.get("aerialways", []) or []:
        g = a.get("geometry") if isinstance(a, dict) else a
        if g:
            lines.append([(p["lat"], p["lon"]) if isinstance(p, dict) else (p[1], p[0]) for p in g])
    return lines


def fetch_traces(bbox):
    traces, page, pages = [], 0, 0
    bs = ",".join(f"{v:.6f}" for v in bbox)
    while page < MAX_PAGES:
        raw = get(f"https://api.openstreetmap.org/api/0.6/trackpoints?bbox={bs}&page={page}")
        root = ET.fromstring(raw)
        n = 0
        for trk in root.iter(NS + "trk"):
            url = (trk.findtext(NS + "url") or "").strip()
            name = (trk.findtext(NS + "name") or "").strip()
            for seg in trk.iter(NS + "trkseg"):
                pts = []
                for tp in seg.iter(NS + "trkpt"):
                    n += 1
                    t = tp.findtext(NS + "time")
                    pts.append((float(tp.get("lat")), float(tp.get("lon")), t))
                traces.append({"url": url, "name": name, "pts": pts})
        pages += 1
        if n < 5000:
            break
        page += 1
    return traces, pages


def parse_t(t):
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def split_segments(pts):
    """Split at gaps > 10 min; returns list of [(lat,lon,ts)]."""
    segs, cur = [], []
    for la, lo, t in pts:
        ts = parse_t(t) if t else None
        if ts is None:
            continue
        if cur and ts - cur[-1][2] > 600:
            segs.append(cur); cur = []
        cur.append((la, lo, ts))
    if cur:
        segs.append(cur)
    return segs


def on_foot(seg):
    if len(seg) < 5:
        return False, "too_short"
    speeds = []
    for a, b in zip(seg, seg[1:]):
        dt, d = b[2] - a[2], hav(a, b)
        if dt <= 0:
            continue
        if dt <= 5 and d > 50:
            return False, "jump"
        speeds.append(d / dt)
    if not speeds:
        return False, "no_time"
    if statistics.median(speeds) > 2.2:
        return False, "fast"
    return True, "ok"


def resample(seg, step=20.0):
    out, acc = [seg[0]], 0.0
    for a, b in zip(seg, seg[1:]):
        acc += hav(a, b)
        if acc >= step:
            out.append(b); acc = 0.0
    if out[-1] is not seg[-1]:
        out.append(seg[-1])
    return out


def elevations(pts):
    res = []
    for i in range(0, len(pts), 100):
        ch = pts[i:i + 100]
        lat = ",".join(f"{p[0]:.5f}" for p in ch)
        lon = ",".join(f"{p[1]:.5f}" for p in ch)
        r = json.loads(get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"))
        res.extend(r.get("elevation", []))
    return res


def near_line(p, lines, tol=30.0):
    for ln in lines:
        for q in ln:
            if hav(p, q) < tol:
                return True
    return False


def pct(v, q):
    if not v:
        return None
    s = sorted(v)
    k = (len(s) - 1) * q
    f = math.floor(k); c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 3)


def process(site, osm):
    bbox, zsrc = zone_for(site, osm)
    lines = aerial_lines(site, osm)
    l, b, r, t = bbox
    inside = lambda p: l <= p[1] <= r and b <= p[0] <= t
    raw, pages = fetch_traces(bbox)
    stats = {"raw_segments": len(raw), "untimed_segments": 0, "rejected": {}}
    by_trace = {}
    for tr in raw:
        if not tr["pts"] or not tr["pts"][0][2]:
            stats["untimed_segments"] += 1
            continue
        key = tr["url"] or tr["name"] or f"anon{id(tr)}"
        for seg in split_segments([p for p in tr["pts"] if inside(p)]):
            ok, why = on_foot(seg)
            if not ok:
                stats["rejected"][why] = stats["rejected"].get(why, 0) + 1
                continue
            by_trace.setdefault(key, []).append(seg)
    traces = []
    for key, segs in by_trace.items():
        dist = dur = moving = ascent = 0.0
        aerial = False
        for seg in segs:
            dur += seg[-1][2] - seg[0][2]
            for a, b2 in zip(seg, seg[1:]):
                d, dt = hav(a, b2), b2[2] - a[2]
                dist += d
                if dt > 0 and 0.2 <= d / dt <= 2.2:
                    moving += dt
            rs = resample(seg)
            try:
                el = elevations(rs) if len(rs) >= 2 else []
            except Exception:
                el, ascent = [], None
            if ascent is None:
                continue
            for i in range(1, len(el)):
                if lines and (near_line(rs[i], lines) or near_line(rs[i - 1], lines)):
                    aerial = True
                    continue
                if el[i] is not None and el[i - 1] is not None and el[i] > el[i - 1]:
                    ascent += el[i] - el[i - 1]
        if dist < 100 or dur <= 0 or dist / dur > 2.2:
            stats["rejected"]["trace_too_fast_or_short"] = stats["rejected"].get("trace_too_fast_or_short", 0) + 1
            continue
        traces.append({
            "trace": key, "n_segments": len(segs),
            "walked_km": round(dist / 1000, 3), "duration_min": round(dur / 60, 1),
            "moving_min": round(moving / 60, 1),
            "avg_speed_mps": round(dist / moving, 2) if moving else None,
            "ascent_m": round(ascent, 1) if ascent is not None else None, "aerialway_overlap": aerial,
        })
    n = len(traces)
    km = [x["walked_km"] for x in traces]
    verdict = "usable" if n >= 5 else "weak" if n >= 2 else "none"
    return {
        "id": site["id"], "name_ko": site["name_ko"], "name_en": site["name_en"],
        "lat": site["lat"], "lng": site["lng"], "zone": {"bbox": bbox, "source": zsrc},
        "pages_fetched": pages, "filter_stats": stats,
        "summary": {
            "n_traces": n, "median_km": pct(km, .5), "p25_km": pct(km, .25), "p75_km": pct(km, .75),
            "median_duration_min": pct([x["duration_min"] for x in traces], .5),
            "median_ascent_m": pct([x["ascent_m"] for x in traces if x["ascent_m"] is not None], .5),
            "median_speed_mps": pct([x["avg_speed_mps"] for x in traces if x["avg_speed_mps"]], .5),
            "coverage": verdict,
        },
        "traces": traces,
    }


def main():
    osm = load_osm()
    only = set(sys.argv[1:])
    prev = {}
    if only and os.path.exists(OUT):
        prev = {x["id"]: x for x in json.load(open(OUT, encoding="utf-8"))["sites"]}
    out = []
    for s in load_sites():
        if only and s["id"] not in only:
            if s["id"] in prev:
                out.append(prev[s["id"]])
            continue
        if s["lat"] is None:
            out.append({"id": s["id"], "error": "no_coords"}); continue
        try:
            res = process(s, osm)
        except Exception as e:
            res = {"id": s["id"], "error": repr(e)}
        out.append(res)
        sm = res.get("summary", {})
        json.dump({"sites": out + [v for k, v in prev.items() if k not in {o["id"] for o in out}]}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        print(s["id"], sm.get("n_traces"), sm.get("median_km"), sm.get("median_ascent_m"), sm.get("coverage"), res.get("error", ""), res.get("filter_stats"), flush=True)
    json.dump({"source": "OSM api/0.6/trackpoints + Open-Meteo elevation",
               "generated": time.strftime("%Y-%m-%d"), "sites": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
