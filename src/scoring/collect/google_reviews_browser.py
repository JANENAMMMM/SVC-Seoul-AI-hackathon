"""Collect Google Maps reviews for a place via headless Chromium (Playwright).

Hackathon demo only: emulates "many Google reviews per attraction". Production
should use the official Google Places API / partner data instead.

Requires (outside the repo's pyproject): pip install playwright && python -m playwright install chromium

Usage:
  python google_reviews_browser.py --place-id ChIJ... --hl en --max-reviews 200 --out out.json
  python google_reviews_browser.py --batch data/scoring/attractions.json --out-dir data/scoring/raw/google_reviews
"""
import argparse
import json
import random
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HANGUL = re.compile(r"[가-힣]")
CJK = re.compile(r"[぀-ヿ一-鿿]")
VI = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I)


def detect_lang(t):
    if HANGUL.search(t):
        return "ko"
    if CJK.search(t):
        return "cjk"
    if VI.search(t):
        return "vi"
    if re.search(r"[a-zA-Z]", t):
        return "en_or_latin"
    return "unknown"


def pause(a=0.8, b=1.8):
    time.sleep(random.uniform(a, b))


JS_EXTRACT = r"""
() => Array.from(document.querySelectorAll('div[data-review-id].jftiEf, div.jftiEf[data-review-id]')).map(el => {
  const t = el.querySelector('.wiI7pd');
  const r = el.querySelector('.kvMYJc');
  const rr = el.querySelector('.fzvQIb');  // alt rating text "5/5"
  const d = el.querySelector('.rsqaWe') || el.querySelector('.xRkPPb');
  return {
    id: el.getAttribute('data-review-id'),
    text: t ? t.innerText : '',
    rating_label: r ? r.getAttribute('aria-label') : (rr ? rr.innerText : null),
    date_text: d ? d.innerText : null,
    has_owner_reply: !!el.querySelector('.CDe7pd'),
  };
})
"""


def collect(page, place_id, hl, max_reviews, log=print):
    url = f"https://www.google.com/maps/place/?q=place_id:{place_id}&hl={hl}"
    t0 = time.time()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    pause(2, 3)
    if "consent.google" in page.url:
        for lab in ["Accept all", "모두 수락", "I agree"]:
            b = page.locator(f'button:has-text("{lab}")')
            if b.count():
                b.first.click()
                break
        pause(2, 3)
    if "sorry" in page.url or page.locator("#captcha-form").count():
        return {"blocked": "captcha", "reviews": [], "secs": time.time() - t0}
    # Reviews tab
    tab = page.locator('button[role="tab"][aria-label*="Reviews"], button[role="tab"][aria-label*="리뷰"]')
    try:
        tab.first.wait_for(timeout=20000)
        tab.first.click()
    except Exception:
        return {"blocked": "no_reviews_tab", "reviews": [], "secs": time.time() - t0}
    pause(2, 3)
    # Sort by newest
    try:
        page.locator('button[aria-label*="Sort"], button[aria-label*="정렬"]').first.click(timeout=8000)
        pause(1, 1.5)
        page.locator('div[role="menuitemradio"]').nth(1).click(timeout=5000)
        pause(2, 3)
    except Exception as e:
        log(f"  sort failed: {e.__class__.__name__}")
    panel = page.locator("div.m6QErb.DxyBCb.kA9KIf.dS8AEf").first
    seen, stall = {}, 0
    while len(seen) < max_reviews and stall < 6:
        for b in page.locator('button.w8nwRe').all()[:20]:  # "More"
            try:
                b.click(timeout=1000)
            except Exception:
                pass
        before = len(seen)
        for r in page.evaluate(JS_EXTRACT):
            if r["id"] and (r["id"] not in seen or len(r["text"]) > len(seen[r["id"]]["text"])):
                seen[r["id"]] = r
        stall = stall + 1 if len(seen) == before else 0
        try:
            panel.evaluate("el => el.scrollBy(0, el.scrollHeight)")
        except Exception:
            page.mouse.wheel(0, 4000)
        pause(1.2, 2.4)
        if page.locator("#captcha-form").count():
            break
    out = []
    for r in list(seen.values())[:max_reviews]:
        m = re.search(r"(\d)", r["rating_label"] or "")
        txt = r["text"].split("(Original)")[-1].strip() if "(Original)" in r["text"] else r["text"].strip()
        out.append({"text": txt, "rating": int(m.group(1)) if m else None, "date_text": r["date_text"],
                    "lang": detect_lang(txt) if txt else None, "hl": hl, "has_owner_reply": r["has_owner_reply"]})
    return {"blocked": None, "reviews": out, "secs": round(time.time() - t0, 1)}


def run(jobs, out_paths, headless=True):
    """jobs: list of (key, place_id, [(hl, max)]). Single browser session, sequential."""
    stats = {}
    with sync_playwright() as p:
        br = p.chromium.launch(headless=headless)
        ctx = br.new_context(locale="en-US", viewport={"width": 1280, "height": 900},
                             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36")
        page = ctx.new_page()
        for key, pid, plan in jobs:
            allrev, meta = [], {}
            for hl, mx in plan:
                res = collect(page, pid, hl, mx)
                allrev += res["reviews"]
                meta[hl] = {"n": len(res["reviews"]), "secs": res["secs"], "blocked": res["blocked"]}
                print(key, hl, meta[hl], flush=True)
                pause(4, 7)
            Path(out_paths[key]).parent.mkdir(parents=True, exist_ok=True)
            json.dump({"place_id": pid, "source": "Google Maps web (Playwright, sort=newest)",
                       "meta": meta, "reviews": allrev},
                      open(out_paths[key], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            stats[key] = meta
        br.close()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--place-id")
    ap.add_argument("--hl", default="en")
    ap.add_argument("--max-reviews", type=int, default=200)
    ap.add_argument("--out")
    ap.add_argument("--batch", help="attractions.json; collects max-reviews en + --max-ko ko per site")
    ap.add_argument("--max-ko", type=int, default=100)
    ap.add_argument("--out-dir", default="data/scoring/raw/google_reviews")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    if a.batch:
        sites = json.load(open(a.batch, encoding="utf-8"))
        sites = [s for s in sites if not a.only or s["id"] in a.only]
        jobs = [(s["id"], s["google"]["place_id"], [("en", a.max_reviews), ("ko", a.max_ko)]) for s in sites]
        run(jobs, {s["id"]: f"{a.out_dir}/{s['id']}.json" for s in sites})
    else:
        run([("single", a.place_id, [(a.hl, a.max_reviews)])], {"single": a.out})
