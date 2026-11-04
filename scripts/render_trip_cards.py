"""trip-cards/template.html에 일정 JSON을 넣어 1080×1350 PNG를 만듭니다.

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
    cards = json.loads(src.read_text())["cards"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for c in cards:
            page = browser.new_page(viewport={"width": 1080, "height": 1350})
            c = {**c, "credit": credit_for(c["photo"]), "photo": (PHOTOS / c["photo"]).as_uri()}
            page.add_init_script(f"window.CARD = {json.dumps(c, ensure_ascii=False)};")
            page.goto((ROOT / "trip-cards" / "template.html").as_uri())
            page.wait_for_timeout(300)
            target = out / f"day{c['day']}.png"
            page.screenshot(path=str(target))
            print("saved", target.relative_to(ROOT))
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
