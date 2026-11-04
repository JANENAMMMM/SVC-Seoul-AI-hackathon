"""Wikimedia Commons에서 여행지별 자유 이용 사진을 수집합니다.

사용: uv run --with pillow --with requests python scripts/collect_place_photos.py [슬러그...]
결과: assets/place-photos/<슬러그>/01.jpg ... 와 credits.json(작가·라이선스·원문 링크)
"""
import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
OUT = Path(__file__).resolve().parent.parent / "assets" / "place-photos"
PER_PLACE = 10
MAX_WIDTH = 1280
HEADERS = {"User-Agent": "banggeoreum-hackathon-photo-collector/1.0 (educational project)"}

PLACES = {
    "bana-hills": ("바나힐", ["Bà Nà Hills", "Golden Bridge Da Nang", "Ba Na Hills cable car", "Ba Na Hills Da Nang"]),
    "marble-mountains": ("오행산", ["Marble Mountains Da Nang", "Ngu Hanh Son", "Marble Mountains Vietnam"]),
    "linh-ung": ("영흥사", ["Linh Ung Pagoda Da Nang", "Lady Buddha Da Nang", "Linh Ung Son Tra", "Linh Ứng pagoda"]),
    "my-khe": ("미케 해변", ["My Khe Beach", "Mỹ Khê beach Da Nang", "Da Nang beach Vietnam"]),
    "dragon-bridge": ("용다리", ["Dragon Bridge Da Nang", "Cầu Rồng Đà Nẵng", "Dragon Bridge Vietnam fire"]),
    "han-market": ("한시장", ["Han Market Da Nang", "Chợ Hàn Đà Nẵng", "Cho Han Da Nang", "Han Market Vietnam"]),
    "da-nang-cathedral": ("다낭 대성당", ["Da Nang Cathedral", "Đà Nẵng Cathedral", "Nhà thờ Chính tòa Đà Nẵng", "Nhà thờ Con Gà", "Rooster Church Da Nang", "Da Nang Cathedral Vietnam", "Church Da Nang pink"]),
    "cham-museum": ("참 조각 박물관", ["Museum of Cham Sculpture", "Cham Museum Da Nang", "Bảo tàng Điêu khắc Chăm"]),
    "asia-park": ("아시아파크", ["Asia Park Da Nang", "Sun Wheel Da Nang", "Sun World Danang Wonders"]),
    "nui-than-tai": ("누이탄타이 온천", ["Núi Thần Tài", "Nui Than Tai Da Nang", "Than Tai mountain hot spring Da Nang", "CVKSN Núi Thần Tài"]),
    "hai-van-pass": ("하이반 고개", ["Hai Van Pass", "Hải Vân Pass", "Hai Van Pass Vietnam road"]),
    "hoi-an-old-town": ("호이안 구시가지", ["Hội An Ancient Town", "Hoi An old town lanterns", "Japanese Covered Bridge Hoi An", "Hoi An Vietnam"]),
    "hoi-an-night-market": ("호이안 야시장", ["Hoi An by night", "Hội An lantern festival", "Lantern Shop in Hoi An", "Hoi An night market"]),
    "cam-thanh": ("껌탄 코코넛 마을", ["Basket Boat and the Bamboo forest", "Cam Thanh Hoi An basket boat", "Cẩm Thanh coconut forest", "Bay Mau coconut"]),
    "my-son": ("미선 유적지", ["My Son Sanctuary", "Mỹ Sơn", "My Son Cham temples", "My Son Vietnam"]),
}

OK_LICENSE = re.compile(r"^(cc0|pd|public domain|cc[- ]by(-sa)?[- ]?(1\.0|2\.0|2\.5|3\.0|4\.0)?)", re.I)
BAD_LICENSE = re.compile(r"\b(nc|nd)\b|fair use|non-?free|gfdl-only", re.I)
BAD_TITLE = re.compile(r"virus|corona|covid|Lam Dong|Ijazah|Cất nóc|map|logo|flag|diagram|plan|screenshot|stamp|coat of arms|\.svg|\.png|\.gif|\.tif|\.pdf", re.I)


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def search(query, limit=50):
    r = requests.get(API, headers=HEADERS, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{query} filetype:bitmap", "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": MAX_WIDTH,
    })
    if r.status_code == 429:
        time.sleep(15)
        return search(query, limit)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    return sorted(pages.values(), key=lambda p: p.get("index", 0))


def candidate(page):
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    lic = strip_html(meta.get("LicenseShortName", {}).get("value"))
    title = page.get("title", "")
    if info.get("mime") != "image/jpeg" or BAD_TITLE.search(title):
        return None
    w, h = info.get("width", 0), info.get("height", 0)
    if w < 1400 or h < 900 or w < h * 1.15:  # 템플릿용 가로형 고해상도만
        return None
    if not lic or BAD_LICENSE.search(lic) or not OK_LICENSE.match(lic):
        return None
    return {
        "title": title, "license": lic, "width": w, "height": h,
        "author": strip_html(meta.get("Artist", {}).get("value")) or "Unknown",
        "source": info.get("descriptionurl"), "license_url": meta.get("LicenseUrl", {}).get("value", ""),
        "download": info.get("thumburl") or info.get("url"),
    }


def collect(slug):
    ko, queries = PLACES[slug]
    folder = OUT / slug
    folder.mkdir(parents=True, exist_ok=True)
    seen, picks = set(), []
    for q in queries:
        for page in search(q):
            c = candidate(page)
            if c and c["title"] not in seen:
                seen.add(c["title"])
                picks.append(c)
        time.sleep(0.5)
    credits = []
    for c in picks:
        if len(credits) >= PER_PLACE:
            break
        try:
            resp = requests.get(c["download"], headers=HEADERS, timeout=60)
            if resp.status_code == 429:
                time.sleep(10)
                resp = requests.get(c["download"], headers=HEADERS, timeout=60)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        except Exception as e:  # noqa: BLE001
            print(f"  skip {c['title']}: {e}")
            continue
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)))
        name = f"{len(credits) + 1:02d}.jpg"
        img.save(folder / name, "JPEG", quality=84, optimize=True)
        print("   +", c["title"])
        credits.append({"file": name, **{k: c[k] for k in ("title", "author", "license", "license_url", "source")}})
        time.sleep(1.0)
    (folder / "credits.json").write_text(json.dumps({"place": ko, "photos": credits}, ensure_ascii=False, indent=2))
    print(f"{ko}({slug}): {len(credits)}/{PER_PLACE}장 (후보 {len(picks)})")
    return len(credits)


if __name__ == "__main__":
    for s in sys.argv[1:] or PLACES:
        collect(s)
