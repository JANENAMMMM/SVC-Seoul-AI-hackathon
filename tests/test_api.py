import pytest
from fastapi.testclient import TestClient

from api.main import app, get_conn
from src.storage import connect


@pytest.fixture
def client(tmp_path):
    conn = connect(tmp_path / "api.db")
    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()
    conn.close()


def test_get_missing(client):
    assert client.get("/api/trips/none").status_code == 404


def test_put_then_get(client, demo_trip):
    body = demo_trip.model_dump(mode="json")
    r = client.put(f"/api/trips/{demo_trip.id}", json=body)
    assert r.status_code == 200 and r.json()["version"] == 1

    r = client.put(f"/api/trips/{demo_trip.id}", json=body)
    assert r.json()["version"] == 2

    r = client.get(f"/api/trips/{demo_trip.id}")
    assert r.status_code == 200 and r.json()["version"] == 2


def test_put_if_match_conflict(client, demo_trip):
    body = demo_trip.model_dump(mode="json")
    client.put(f"/api/trips/{demo_trip.id}", json=body)
    ok = client.put(f"/api/trips/{demo_trip.id}", json=body, headers={"If-Match": "1"})
    assert ok.status_code == 200
    stale = client.put(f"/api/trips/{demo_trip.id}", json=body, headers={"If-Match": "1"})
    assert stale.status_code == 409


def test_put_id_mismatch(client, demo_trip):
    body = demo_trip.model_dump(mode="json")
    assert client.put("/api/trips/other", json=body).status_code == 400


def test_put_invalid_body(client, demo_trip):
    body = demo_trip.model_dump(mode="json")
    body["parents"][0]["walking_grade"] = "fast"
    assert client.put(f"/api/trips/{demo_trip.id}", json=body).status_code == 422
