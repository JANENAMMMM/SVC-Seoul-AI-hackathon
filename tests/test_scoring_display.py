from fastapi.testclient import TestClient

from api.main import app
from src.scoring.display import cautions, mode_view


def test_cautions_surface_hard_dimension_hidden_by_average():
    mode = {"score": 4, "dimensions": {"climb": {"score": 8}, "walking": {"score": 2},
                                       "heat": {"score": 3}, "crowd": {"score": 2}}}
    assert mode_view(mode) == {"grade": "중", "cautions": ["계단·오르막"]}
    assert cautions({"climb": {"score": 6}}) == []


def test_places_api_exposes_grade_and_cautions():
    places = {p["place_id"]: p for p in TestClient(app).get("/api/scoring/places").json()}
    std = places["dad-02"]["modes"]["standard"]
    assert std["score"] == 6 and std["grade"] == "상"
    assert "계단·오르막" in std["cautions"]
    detail = TestClient(app).get("/api/scoring/places/dad-02").json()
    assert detail["modes"]["standard"]["cautions"] == std["cautions"]
