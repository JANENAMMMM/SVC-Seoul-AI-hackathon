"""Security boundaries and provenance checks, without network or paid model calls."""
import time

from fastapi.testclient import TestClient
from api.main import app
from api import ui


def test_md_session_fails_closed_without_configuration(monkeypatch):
    monkeypatch.delenv("HITL_MD_TOKEN", raising=False)
    with TestClient(app) as client:
        assert client.post("/api/ui/md/session", json={"token": "anything"}).status_code == 403
        assert client.get("/api/ui/md/feedback").status_code == 403
        assert client.get("/api/hitl/feedback").status_code == 403


def test_md_http_only_session_origin_and_logout(monkeypatch):
    monkeypatch.setenv("HITL_MD_TOKEN", "test-only-not-a-real-secret")
    with TestClient(app) as client:
        login = client.post("/api/ui/md/session", json={"token": "test-only-not-a-real-secret"})
        assert login.status_code == 200
        assert "HttpOnly" in login.headers["set-cookie"]
        assert "SameSite=strict" in login.headers["set-cookie"]
        assert "test-only" not in login.text
        assert client.get("/api/ui/md/evaluation").status_code == 200
        denied = client.delete("/api/ui/md/session", headers={"Origin": "https://foreign.example"})
        assert denied.status_code == 403
        assert client.delete("/api/ui/md/session").status_code == 200
        assert client.get("/api/ui/md/evaluation").status_code == 403


def test_expired_session_cannot_access_md():
    token = "expired-test-session"
    ui.SESSIONS[ui.digest(token)] = time.time() - 1
    with TestClient(app) as client:
        client.cookies.set("bangeoreum_md", token)
        assert client.get("/api/ui/md/evaluation").status_code == 403
    ui.SESSIONS.pop(ui.digest(token), None)


def test_current_score_explanations_match_valid_runs_and_have_climate():
    with TestClient(app) as client:
        data = client.get("/api/ui/evidence/dad-02").json()
        assert data["verification"]["matched_dimensions"] == 4
        assert 0 < data["verification"]["valid"] <= data["verification"]["runs"]
        assert [d["weight"] for d in data["dimensions"]] == [3, 3, 2, 1]
        assert len(data["climate"]["monthly_mean_apparent_max_c"]) == 12
        assert data["forecast"]["connected"] is False
        assert any(i.startswith("climate:") for d in data["dimensions"] for c in d["lower_conditions"] + d["upper_conditions"] for i in c["evidence_ids"])


def test_share_snapshot_excludes_private_profile_and_request():
    snapshot = ui.share_snapshot({"request": {"start_date": "2026-12-07", "travelers": [{"age": 64, "gender": "female"}]},
                                  "days": [{"day": 1, "difficulty": 6, "total_walk_min": 40,
                                            "stops": [{"type": "attraction", "place_id": "dad-02", "mode": "standard", "start": "09:00", "name": "오행산"}]}]}, "엄마")
    assert "travelers" not in str(snapshot) and "gender" not in str(snapshot)
    assert snapshot["days"][0]["stops"][0]["cautions"]
    assert snapshot["start_date"] == "2026-12-07"


def test_missing_provenance_fails_visibly_instead_of_inventing_explanation(monkeypatch):
    monkeypatch.setattr(ui, "snapshot_runs", lambda *_: [])
    out = ui.evidence_detail("dad-02")
    assert out["verification"]["issue"]
    assert out["verification"]["matched_dimensions"] == 0
    assert all(d["rationale"] is None for d in out["dimensions"])


def test_invalid_share_choice_and_invalid_id_do_not_enter_db():
    app.dependency_overrides[ui.connection] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.post("/api/ui/shares/not-a-real-share/opinions", json={"day": 0, "choice": "자동 승인"})
            assert response.status_code == 422
            assert client.get("/api/ui/evidence/not-a-place").status_code == 404
    finally:
        app.dependency_overrides.pop(ui.connection, None)
