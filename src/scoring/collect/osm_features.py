"""Objective walking-burden features from OpenStreetMap + Open-Meteo DEM.

Usage: python src/scoring/collect/osm_features.py [site_id ...]
Outputs: data/scoring/raw/osm_<id>.json, data/scoring/derived/osm_features.json
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

UA = "bangeoreum-research/0.1 (hackathon)"
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]
ELEV = "https://api.open-meteo.com/v1/elevation"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RAW = os.path.join(ROOT, "data", "scoring", "raw")
DER = os.path.join(ROOT, "data", "scoring", "derived")

# id -> (name regex, center lat, lon, search radius m, mode, buffer m)
# mode "poly": prefer polygon by name; "buffer": point/line site -> buffer zone around anchor
SITES = {
    "dad-01": ("Bà Nà|Ba Na", 15.996, 107.990, 8000, "poly", 0),
    "dad-02": ("Ngũ Hành Sơn|Marble Mountain", 16.004, 108.263, 3000, "poly", 0),
    "dad-03": ("Phố cổ Hội An|Hoi An Ancient Town|Hội An Ancient", 15.877, 108.328, 3000, "poly", 0),
    "dad-04": ("Linh Ứng|Linh Ung", 16.100, 108.278, 3000, "poly", 0),
    "dad-05": ("Mỹ Khê|My Khe", 16.062, 108.247, 3000, "buffer", 300),
    "dad-06": ("Cầu Rồng|Dragon Bridge", 16.0612, 108.2272, 1500, "buffer", 300),
    "dad-07": ("Chợ Hàn|Han Market", 16.0683, 108.2243, 1500, "poly", 0),
    "dad-08": ("Nhà thờ Chính tòa Đà Nẵng|Con Gà|Da Nang Cathedral|Chính tòa", 16.0667, 108.2232, 1500, "poly", 0),
    "dad-09": ("Điêu khắc Chăm|Cham Sculpture|Bảo tàng Chăm", 16.0604, 108.2236, 1500, "poly", 0),
    "dad-10": ("Asia Park|Danang Wonders|Châu Á|Sun World Đà Nẵng", 16.0393, 108.2280, 2000, "poly", 0),
    "dad-11": ("Thần Tài|Than Tai", 15.966, 108.035, 6000, "poly", 0),
    "dad-12": ("Mỹ Sơn|My Son", 15.764, 108.124, 4000, "poly", 0),
    "dad-13": ("Hải Vân|Hai Van", 16.193, 108.128, 4000, "buffer", 300),
    "dad-14": ("Chợ đêm|Night Market", 15.8767, 108.3256, 1500, "buffer", 300),
    "dad-15": ("Bảy Mẫu|Bay Mau|Cẩm Thanh|Coconut", 15.888, 108.371, 3000, "poly", 0),
}
GOOD_KEYS = ("tourism", "historic", "leisure", "natural", "amenity", "landuse",
             "building", "boundary", "place", "shop", "mountain_pass")
PED = {"footway", "path", "pedestrian", "steps", "living_street"}
_last = [0.0]


def http_get(url, data=None, timeout=300):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def overpass(q):
    body = urllib.parse.urlencode({"data": "[out:json][timeout:240];" + q}).encode()
    err = None
    for ep in OVERPASS:
        for _ in range(3):
            wait = 2.5 - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            try:
                res = http_get(ep, body)
                _last[0] = time.time()
                return res
            except Exception as e:  # noqa
                _last[0] = time.time()
                err = e
                time.sleep(15)
    raise RuntimeError(f"overpass failed: {err}")


# ---------- geometry ----------
def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def ring_area(ring):
    if len(ring) < 3:
        return 0.0
    lat0 = sum(p[0] for p in ring) / len(ring)
    k = 111320 * math.cos(math.radians(lat0))
    xy = [(p[1] * k, p[0] * 110540) for p in ring]
    s = sum(xy[i][0] * xy[i - 1][1] - xy[i - 1][0] * xy[i][1] for i in range(len(xy)))
    return abs(s) / 2


def pip(pt, ring):
    y, x = pt
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi, xi = ring[i]
        yj, xj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi:
            inside = not inside
        j = i
    return inside


def join_rings(segs):
    """Assemble outer rings from relation member ways (lists of (lat,lon))."""
    segs = [list(s) for s in segs if len(s) > 1]
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if cur[0] == cur[-1] and len(cur) >= 4:
            rings.append(cur)
    return rings


def circle(lat, lon, r, n=36):
    return [(lat + (r / 110540) * math.sin(2 * math.pi * i / n),
             lon + (r / (111320 * math.cos(math.radians(lat)))) * math.cos(2 * math.pi * i / n))
            for i in range(n + 1)]


def el_geom(e):
    if e["type"] == "node":
        return None, (e["lat"], e["lon"])
    if e["type"] == "way":
        g = [(p["lat"], p["lon"]) for p in e.get("geometry", [])]
        if len(g) >= 4 and g[0] == g[-1]:
            return [g], g[len(g) // 2]
        return None, g[len(g) // 2] if g else None
    outer = [[(p["lat"], p["lon"]) for p in m.get("geometry", [])]
             for m in e.get("members", []) if m.get("type") == "way" and m.get("role") in ("outer", "")]
    rings = join_rings(outer)
    c = e.get("center")
    anchor = (c["lat"], c["lon"]) if c else (rings[0][0] if rings else None)
    return (rings or None), anchor


# ---------- step 1: match site ----------
def match_site(sid):
    rx, lat, lon, rad, mode, buf = SITES[sid]
    q = f'nwr(around:{rad},{lat},{lon})[~"^(name|name:en|alt_name|name:vi)$"~"{rx}",i]'
    res = overpass(f"({q};is_in({lat},{lon})->.a;way(pivot.a);rel(pivot.a););out geom center tags;")
    cands = []
    for e in res.get("elements", []):
        t = e.get("tags", {})
        if not any(k in t for k in GOOD_KEYS) and t.get("highway") is None and t.get("man_made") is None:
            continue
        if t.get("highway") in ("bus_stop",) or t.get("public_transport"):
            continue
        rings, anchor = el_geom(e)
        area = sum(ring_area(r) for r in rings) if rings else 0.0
        cands.append({"e": e, "rings": rings, "anchor": anchor, "area": area,
                      "dist": hav(anchor, (lat, lon)) if anchor else 1e9})
    rec = {"candidates_n": len(cands)}
    polys = [c for c in cands if c["rings"] and 300 < c["area"] < 40e6 and not c["e"]["tags"].get("highway")]
    best = None
    if mode == "poly" and polys:
        # prefer tourism/historic/leisure tagged, then larger area
        def score(c):
            t = c["e"]["tags"]
            pri = 2 if any(k in t for k in ("tourism", "historic", "leisure")) else (1 if "amenity" in t or "shop" in t else 0)
            return (pri, c["area"])
        best = max(polys, key=score)
        rec.update(zone_type="osm_polygon", rings=best["rings"], area_m2=round(best["area"]))
        rec["match_method"] = f"name regex '{rx}' within {rad}m; picked polygon by tag priority+area"
    else:
        pts = sorted([c for c in cands if c["anchor"]], key=lambda c: c["dist"])
        if pts:
            best = pts[0]
            anchor = best["anchor"]
            if best["rings"] and best["area"] < 1e6:
                anchor = (sum(p[0] for p in best["rings"][0]) / len(best["rings"][0]),
                          sum(p[1] for p in best["rings"][0]) / len(best["rings"][0]))
        else:
            anchor = (lat, lon)
        b = buf or 300
        rec.update(zone_type=f"buffer_{b}m", rings=[circle(anchor[0], anchor[1], b)],
                   area_m2=round(math.pi * b * b))
        rec["match_method"] = (f"linear/point site: {b}m buffer around "
                               + ("nearest OSM name match" if best else "manual seed coordinate (no OSM match)"))
    if best:
        t = best["e"]["tags"]
        rec.update(osm_type=best["e"]["type"], osm_id=best["e"]["id"], osm_name=t.get("name"),
                   osm_tags={k: v for k, v in t.items() if k in GOOD_KEYS + ("name:en", "wheelchair", "highway", "man_made")})
    return rec


# ---------- step 2: ways inside ----------
def bbox_of(rings):
    la = [p[0] for r in rings for p in r]
    lo = [p[1] for r in rings for p in r]
    return min(la), min(lo), max(la), max(lo)


def inside(pt, rings):
    return any(pip(pt, r) for r in rings)


def fetch_infra(rings):
    s, w, n, e = bbox_of(rings)
    b = f"({s},{w},{n},{e})"
    q = (f'(way["highway"~"^(footway|path|pedestrian|steps|living_street|service|track|corridor)$"]{b};'
         f'way["aerialway"]{b};node["aerialway"]{b};'
         f'nwr["highway"="elevator"]{b};nwr["conveying"]{b};'
         f'way["railway"~"funicular|narrow_gauge|monorail|light_rail|miniature"]{b};'
         f'nwr["amenity"="bench"]{b};nwr["amenity"="toilets"]{b};nwr["amenity"="shelter"]{b};);out geom tags;')
    return overpass(q).get("elements", [])


def is_ped(t):
    h = t.get("highway")
    if h in PED or h == "corridor":
        return True
    if h in ("service", "track"):
        return t.get("foot") in ("yes", "designated", "permissive")
    return False


def clip(g, rings):
    """segments whose midpoint lies inside -> list of contiguous pieces"""
    pieces, cur = [], []
    for a, b in zip(g, g[1:]):
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if inside(m, rings):
            if not cur:
                cur = [a]
            cur.append(b)
        elif cur:
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    return pieces


def plen(p):
    return sum(hav(a, b) for a, b in zip(p, p[1:]))


def resample(p, step=40):
    out = [p[0]]
    acc = 0.0
    for a, b in zip(p, p[1:]):
        d = hav(a, b)
        acc += d
        if acc >= step:
            out.append(b)
            acc = 0.0
    if out[-1] != p[-1]:
        out.append(p[-1])
    return out


def elevations(pts):
    out = []
    for i in range(0, len(pts), 100):
        ch = pts[i:i + 100]
        url = ELEV + "?latitude=" + ",".join(f"{p[0]:.6f}" for p in ch) + \
            "&longitude=" + ",".join(f"{p[1]:.6f}" for p in ch)
        for k in range(4):
            try:
                out += http_get(url, timeout=60)["elevation"]
                break
            except Exception as ex:
                print("elev retry", ex, flush=True)
                time.sleep(10 * (k + 1))
        else:
            out += [None] * len(ch)
        time.sleep(0.6)
    return out


def gain(z):
    z = [v for v in z if v is not None]
    up = sum(max(0, b - a) for a, b in zip(z, z[1:]))
    dn = sum(max(0, a - b) for a, b in zip(z, z[1:]))
    return up, dn


def analyse(sid, rec, els):
    rings = rec["rings"]
    ped, aer, rail = [], [], []
    feats = {"elevator": 0, "conveying": 0, "aerialway_nodes": 0, "bench": 0, "toilets": 0, "shelter": 0}
    for e in els:
        t = e.get("tags", {})
        if e["type"] == "node" or "geometry" not in e and "lat" in e:
            pt = (e["lat"], e["lon"])
            if not inside(pt, rings):
                continue
            if t.get("highway") == "elevator": feats["elevator"] += 1
            if "conveying" in t: feats["conveying"] += 1
            if "aerialway" in t: feats["aerialway_nodes"] += 1
            for k in ("bench", "toilets", "shelter"):
                if t.get("amenity") == k: feats[k] += 1
            continue
        g = [(p["lat"], p["lon"]) for p in e.get("geometry", []) if p]
        if len(g) < 2:
            continue
        pieces = clip(g, rings)
        if "aerialway" in t:
            # an aerialway counts if any part crosses/touches the zone
            if pieces or inside(g[0], rings) or inside(g[-1], rings):
                aer.append({"id": e["id"], "type": t["aerialway"], "name": t.get("name"),
                            "length_m": round(plen(g)), "ends": [g[0], g[-1]]})
            continue
        if not pieces:
            continue
        if "railway" in t:
            rail.append({"id": e["id"], "railway": t["railway"], "name": t.get("name"),
                         "length_m": round(sum(plen(p) for p in pieces))})
            continue
        if t.get("highway") == "elevator": feats["elevator"] += 1
        if "conveying" in t: feats["conveying"] += 1
        if is_ped(t):
            ped.append({"id": e["id"], "t": t, "pieces": pieces, "len": sum(plen(p) for p in pieces)})

    tot = sum(w["len"] for w in ped)
    steps = [w for w in ped if w["t"].get("highway") == "steps"]
    sc = [int(w["t"]["step_count"]) for w in steps if str(w["t"].get("step_count", "")).isdigit()]

    def cov(key, pool=ped):
        if not pool:
            return None
        return round(100 * sum(w["len"] for w in pool if key in w["t"]) / max(1e-9, sum(w["len"] for w in pool)), 1)

    # elevation sampling (cap ~400 pts)
    step = 40
    while sum(len(resample(p, step)) for w in ped for p in w["pieces"]) > 400 and step < 2000:
        step *= 1.6
    samples = []  # (way_idx, piece_idx, pt)
    for wi, w in enumerate(ped):
        for pi, p in enumerate(w["pieces"]):
            for pt in resample(p, step):
                samples.append((wi, pi, pt))
    zs = elevations([s[2] for s in samples]) if samples else []
    elev = {"sample_step_m": round(step), "n_samples": len(samples)}
    if zs and any(z is not None for z in zs):
        valid = [z for z in zs if z is not None]
        elev.update(min_m=min(valid), max_m=max(valid), range_m=round(max(valid) - min(valid), 1))
        per = {}
        for (wi, pi, pt), z in zip(samples, zs):
            per.setdefault((wi, pi), []).append((pt, z))
        # main walkway = longest single piece
        mk = max(per, key=lambda k: plen(ped[k[0]]["pieces"][k[1]]))
        up, dn = gain([z for _, z in per[mk]])
        elev.update(main_way_id=ped[mk[0]]["id"], main_way_len_m=round(plen(ped[mk[0]]["pieces"][mk[1]])),
                    main_way_name=ped[mk[0]]["t"].get("name"),
                    main_way_climb_m=round(max(up, dn), 1))
        net_up = sum(max(gain([z for _, z in v])) for v in per.values())
        elev["network_climb_m"] = round(net_up, 1)
        # walk-only: cluster pedestrian samples by nearest aerialway terminal (<=800 m);
        # climb you still walk = max elevation range inside a terminal cluster;
        # unserved samples form their own cluster.
        if aer:
            terms = [pt for a in aer for pt in a["ends"]]
            clusters = {}
            for (wi, pi, pt), z in zip(samples, zs):
                if z is None:
                    continue
                d, ti = min((hav(pt, tp), i) for i, tp in enumerate(terms))
                clusters.setdefault(ti if d <= 800 else -1, []).append(z)
            rngs = {k: max(v) - min(v) for k, v in clusters.items() if v}
            elev["walk_only_climb_m"] = round(max(rngs.values()), 1) if rngs else None
            elev["walk_only_method"] = "max elevation range within 800m clusters around aerialway terminals (+unserved cluster)"
        else:
            elev["walk_only_climb_m"] = elev["range_m"]
            elev["walk_only_method"] = "no aerialway: equals walkway elevation range"
    area = rec["area_m2"]
    out = {
        "pedestrian_way_count": len(ped),
        "pedestrian_length_m": round(tot),
        "pedestrian_density_m_per_ha": round(tot / (area / 1e4), 1) if area else None,
        "steps_count": len(steps),
        "steps_length_m": round(sum(w["len"] for w in steps)),
        "step_count_sum": sum(sc) if sc else None,
        "steps_with_step_count": len(sc),
        "aerialway": bool(aer), "aerialways": aer,
        "rail_shuttle": rail,
        "elevator_count": feats["elevator"], "conveying_count": feats["conveying"],
        "bench_count": feats["bench"], "toilets_count": feats["toilets"], "shelter_count": feats["shelter"],
        "elevation": elev,
        "quality": {
            "surface_cov_pct": cov("surface"), "incline_cov_pct": cov("incline"),
            "sac_scale_cov_pct": cov("sac_scale"), "wheelchair_cov_pct": cov("wheelchair"),
            "step_count_cov_pct_of_steps": round(100 * len(sc) / len(steps), 1) if steps else None,
            "handrail_cov_pct_of_steps": cov("handrail", steps) if steps else None,
            "dem": "Open-Meteo elevation (Copernicus GLO-90, ~90 m)",
        },
    }
    for a in aer:
        a.pop("ends", None)
    return out


def flags(r):
    f = []
    if r["zone_type"].startswith("buffer"): f.append("zone_is_buffer")
    if r["pedestrian_length_m"] < 200: f.append("sparse_walkway_mapping")
    if r["steps_count"] and not r["steps_with_step_count"]: f.append("steps_without_step_count")
    q = r["quality"]
    if (q["surface_cov_pct"] or 0) < 30: f.append("low_surface_coverage")
    if (q["incline_cov_pct"] or 0) < 5: f.append("incline_mostly_missing")
    if r["area_m2"] and r["area_m2"] < 20000: f.append("small_area_dem_90m_unreliable")
    return f


def run(ids):
    seeds = {s["id"]: s for s in json.load(open(os.path.join(ROOT, "data", "scoring", "attractions_seed.json"), encoding="utf-8"))}
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(DER, exist_ok=True)
    outp = os.path.join(DER, "osm_features.json")
    results = {}
    if os.path.exists(outp):
        results = {r["id"]: r for r in json.load(open(outp, encoding="utf-8"))}
    for sid in ids:
        print("==", sid, seeds[sid]["name_en"], flush=True)
        rec = match_site(sid)
        els = fetch_infra(rec["rings"])
        with open(os.path.join(RAW, f"osm_{sid}.json"), "w", encoding="utf-8") as f:
            json.dump([{"type": e["type"], "id": e["id"], "tags": e.get("tags", {}),
                        "geometry": e.get("geometry"), "lat": e.get("lat"), "lon": e.get("lon")} for e in els],
                      f, ensure_ascii=False)
        r = {"id": sid, "name_ko": seeds[sid]["name_ko"], "name_en": seeds[sid]["name_en"]}
        r.update({k: v for k, v in rec.items() if k != "rings"})
        r.update(analyse(sid, rec, els))
        r["quality_flags"] = flags(r)
        results[sid] = r
        print(json.dumps({k: r[k] for k in ("osm_name", "zone_type", "area_m2", "pedestrian_length_m", "steps_count", "aerialway")
                          if k in r}, ensure_ascii=False), r["elevation"].get("walk_only_climb_m"), flush=True)
        with open(outp, "w", encoding="utf-8") as f:
            json.dump([results[k] for k in sorted(results)], f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    run(sys.argv[1:] or list(SITES))
