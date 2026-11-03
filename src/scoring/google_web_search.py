"""Google organic search through SerpApi; no key or raw response is logged."""
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen


def search(query, *, limit=5, opener=urlopen):
    key = os.environ.get("SERPAPI_KEY")
    if not key:
        raise RuntimeError("SERPAPI_KEY missing")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be nonempty")
    limit = max(1, min(int(limit), 10))
    url = "https://serpapi.com/search.json?" + urlencode(
        {"engine": "google", "q": query.strip(), "hl": "en", "num": limit, "api_key": key})
    try:
        with opener(url, timeout=15) as response:
            data = json.load(response)
    except Exception as exc:
        raise RuntimeError("Google search request failed") from None
    if data.get("error"):
        raise RuntimeError("Google search provider returned an error")
    return [{"title": r.get("title"), "url": r["link"], "snippet": r.get("snippet")}
            for r in data.get("organic_results", [])[:limit] if r.get("link")]
