from fastapi.testclient import TestClient

from api.main import app


def _profile(client):
    return client.post("/api/profile", json={"age": 68, "gender": "female"}).json()


def test_plan_then_refine_through_api():
    with TestClient(app) as client:
        body = {"travelers": [_profile(client)], "place_ids": ["dad-02", "dad-05", "dad-07", "dad-03"],
                "days": 3, "start_date": "2026-12-07"}
        res = client.post("/api/planner/plan", json=body)
        assert res.status_code == 200
        itinerary = res.json()
        assert len(itinerary["days"]) == 3 and itinerary["package"]["peak"] >= 1

        refined = client.post("/api/planner/refine", json={
            "itinerary": itinerary,
            "commands": [{"op": "move_place", "place_id": "dad-05", "day": 3}],
        })
        assert refined.status_code == 200
        data = refined.json()
        assert data["clarification"] is None and data["applied_commands"][0]["op"] == "move_place"
        stops = [s for d in data["itinerary"]["days"] if d["day"] == 3 for s in d["stops"]]
        assert any(s["place_id"] == "dad-05" for s in stops)


def test_unknown_place_returns_422():
    with TestClient(app) as client:
        body = {"travelers": [_profile(client)], "place_ids": ["dad-99"], "days": 1}
        assert client.post("/api/planner/plan", json=body).status_code == 422


def test_invalid_command_shape_is_rejected():
    with TestClient(app) as client:
        body = {"travelers": [_profile(client)], "place_ids": ["dad-05"], "days": 1}
        itinerary = client.post("/api/planner/plan", json=body).json()
        res = client.post("/api/planner/refine", json={"itinerary": itinerary, "commands": [{"op": "fly_away"}]})
        assert res.status_code == 422
