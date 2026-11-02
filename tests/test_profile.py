from fastapi.testclient import TestClient

from api.main import app
from src.profile.walking_speed import compute_walking_speed


def test_walking_speed_known_band():
    speed = compute_walking_speed(67, "female")
    assert speed is not None
    assert speed.age_band == "65~69세"
    assert speed.base_speed_mps == 1.0525


def test_walking_speed_open_ended_band():
    speed = compute_walking_speed(85, "male")
    assert speed is not None
    assert speed.age_band == "80세 이상"
    assert speed.base_speed_mps == 0.9366


def test_walking_speed_under_table_range_is_none():
    assert compute_walking_speed(40, "female") is None


def test_create_profile_computes_walking_speed_and_keeps_food_defaults():
    with TestClient(app) as client:
        response = client.post("/api/profile", json={"age": 63, "gender": "male"})
    assert response.status_code == 200
    body = response.json()
    assert body["walking_speed"] == {"age_band": "60~64세", "base_speed_mps": 1.1489}
    assert body["local_food"] == "unknown"
    assert body["venues"] == ["unknown"]
    assert body["avoid_ingredients"] == []


def test_create_profile_under_50_has_null_walking_speed():
    with TestClient(app) as client:
        response = client.post("/api/profile", json={"age": 30, "gender": "female"})
    assert response.status_code == 200
    assert response.json()["walking_speed"] is None
