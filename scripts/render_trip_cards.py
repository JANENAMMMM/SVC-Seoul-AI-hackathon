"""trip-cards/template.html에 일정 JSON을 넣어 여행지당 1080×1350 PNG 한 장을 만듭니다.

사용: uv run --with playwright --with pillow python scripts/render_trip_cards.py [입력.json] [출력폴더]
기본값: trip-cards/sample.json → trip-cards/out/
사진 작가·라이선스는 assets/place-photos/<슬러그>/credits.json에서 자동으로 읽어 카드에 넣습니다.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "assets" / "place-photos"


def credit_for(photo: str) -> str:
    slug, name = photo.split("/")
    info = json.loads((PHOTOS / slug / "credits.json").read_text())
    p = next(x for x in info["photos"] if x["file"] == name)
    author = p["author"] if len(p["author"]) <= 22 else p["author"][:20] + "…"
    return f"{author} · {p['license']}"


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "trip-cards" / "sample.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "trip-cards" / "out"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    days = json.loads(src.read_text())["days"]
    flat = [(d["day"], i + 1, s) for d in days for i, s in enumerate(d["stops"])]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for n, (day, order, s) in enumerate(flat):
            route = [
                {"day": d, "name": x["place"], "time": x["time"], "state": "past" if k < n else "cur" if k == n else "next"}
                for k, (d, _, x) in enumerate(flat)
            ]
            c = {"day": day, "order": order, **{k: s[k] for k in ("time", "place", "desc")}, "place_vi": s.get("place_vi", ""),
                 "credit": credit_for(s["photo"]), "photo": (PHOTOS / s["photo"]).as_uri(), "route": route}
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            page.add_init_script(f"window.CARD = {json.dumps(c, ensure_ascii=False)};")
            page.goto((ROOT / "trip-cards" / "template.html").as_uri())
            page.wait_for_timeout(300)
            target = out / f"{n + 1:02d}-day{day}-{order}.png"
            page.screenshot(path=str(target))
            print("saved", target.relative_to(ROOT))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
