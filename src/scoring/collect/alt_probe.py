"""Alt objective measures probe: OSM public GPS traces inside attraction bboxes.

Usage: python -I src/scoring/collect/alt_probe.py
Counts trackpoints / distinct traces, and for traces with timestamps (identifiable/trackable)
estimates walked distance, climb (if <ele>), duration.
"""
import json, math, sys, urllib.request, xml.etree.ElementTree as ET

UA = "bangeoreum-research/0.1 (hackathon)"
SITES = {
    "ba_na_hills": (107.975, 15.985, 108.005, 16.010),
    "marble_mountains": (108.255, 15.995, 108.272, 16.010),
}
NS = {"g": "http://www.topografix.com/GPX/1/0"}


def hav(a, b):
    R = 6371000.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def fetch(bbox, page):
    url = "https://api.openstreetmap.org/api/0.6/trackpoints?bbox=%s&page=%d" % (",".join(map(str, bbox)), page)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return ET.fromstring(r.read())


def probe(bbox, max_pages=5):
    pts, trk_total, trk_timed = 0, 0, []
    for p in range(max_pages):
        root = fetch(bbox, p)
        trks = root.findall("g:trk", NS)
        n = 0
        for t in trks:
            trk_total += 1
            for seg in t.findall("g:trkseg", NS):
                ps = seg.findall("g:trkpt", NS)
                n += len(ps)
                times = [x.find("g:time", NS) for x in ps]
                if ps and all(tt is not None for tt in times) and len(ps) > 10:
                    co = [(float(x.get("lat")), float(x.get("lon"))) for x in ps]
                    d = sum(hav(co[i], co[i + 1]) for i in range(len(co) - 1))
                    eles = [x.find("g:ele", NS) for x in ps]
                    climb = None
                    if all(e is not None for e in eles):
                        ev = [float(e.text) for e in eles]
                        climb = sum(max(0, ev[i + 1] - ev[i]) for i in range(len(ev) - 1))
                    trk_timed.append({"url": (t.findtext("g:url", None, NS)), "pts": len(ps),
                                      "dist_m": round(d), "climb_m": climb,
                                      "t0": times[0].text, "t1": times[-1].text})
        pts += n
        if n < 5000:
            break
    return {"points": pts, "track_segments": trk_total, "timed_segments": len(trk_timed), "timed": trk_timed[:20]}


if __name__ == "__main__":
    out = {k: probe(b) for k, b in SITES.items()}
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
