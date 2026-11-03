from fastapi.testclient import TestClient

from api.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scoring_catalog_and_confirmed_itinerary():
    with TestClient(app) as client:
        catalog = client.get("/api/scoring/places")
        assert catalog.status_code == 200 and len(catalog.json()) == 15
        detail = client.get("/api/scoring/places/dad-02")
        assert detail.json()["modes"]["short"]["score"] == 5
        assert detail.json()["modes"]["short"]["dimensions"]["climb"]["source_run_id"]
        assert client.get("/api/scoring/places/nope").status_code == 404
        missing_route = client.post("/api/scoring/packages/evaluate", json={"days": [[
            {"place_id": "dad-02", "mode": "short", "source_ref": "", "route_note": ""}]]})
        assert missing_route.status_code == 422
        result = client.post("/api/scoring/packages/evaluate", json={"days": [[
            {"place_id": "dad-02", "mode": "short", "source_ref": "schedule p2",
             "route_note": "elevator and temples only"}]]})
        assert result.status_code == 200 and result.json()["peak"] == 5
