import io
import json

import pytest

from src.scoring.google_web_search import search
from src.scoring.judge import TOOLS, cache_web


def test_google_search_tool_uses_existing_key_without_exposing_it(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "private-test-key")
    urls = []

    def opener(url, timeout):
        urls.append(url)
        assert timeout == 15
        return io.BytesIO(json.dumps({"organic_results": [
            {"title": "A review", "link": "https://example.org/review", "snippet": "stairs remain"},
            {"title": "No link"}]}).encode())

    assert search("Marble Mountains stairs", opener=opener) == [
        {"title": "A review", "url": "https://example.org/review", "snippet": "stairs remain"}]
    assert "engine=google" in urls[0] and "api_key=private-test-key" in urls[0]
    assert any(t["name"] == "google_web_search" for t in TOOLS)


def test_google_search_needs_key_and_rejects_provider_error(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SERPAPI_KEY missing"):
        search("query")
    monkeypatch.setenv("SERPAPI_KEY", "private-test-key")

    def opener(url, timeout):
        return io.BytesIO(b'{"error":"private provider detail"}')

    with pytest.raises(RuntimeError, match="provider returned an error") as exc:
        search("query", opener=opener)
    assert "private-test-key" not in str(exc.value)


def test_search_result_can_be_cited_and_cached(monkeypatch):
    saved = []
    monkeypatch.setattr("src.scoring.judge.db.upsert", lambda conn, table, rows: saved.extend(rows))
    result = {"place_id": "dad-02", "output": {"dimensions": {"climb": {
        "evidence_ids": ["https://example.org/review"]}}},
        "web_results": {"https://example.org/review": {"title": "A review", "excerpt": "stairs remain"}},
        "web_queries": ["Marble Mountains stairs"]}
    cache_web(None, result)
    assert len(saved) == 1
    assert saved[0]["url"] == "https://example.org/review"
    assert saved[0]["excerpt"] == "stairs remain"
