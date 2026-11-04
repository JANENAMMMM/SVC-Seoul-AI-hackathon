"""Actual HTTP + Postgres verification. Deletes only rows created by this run."""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.database import connect_db


def main():
    tid = None
    checks = 0
    try:
        with httpx.Client(base_url="http://127.0.0.1:8131", timeout=60) as client:
            profile = client.post("/api/profile", json={"age": 64, "gender": "female", "walking_duration": "1_2hour"}).json()
            res = client.post("/api/ui/trips", json={"request": {"travelers": [profile], "place_ids": ["dad-02", "dad-05"], "days": 2},
                                                         "conditions": {"name": "UI 검증용", "avoid_tags": ["계단·오르막"], "must_places": ["dad-02"]}})
            assert res.status_code == 201, f"create status {res.status_code}"
            trip = res.json()
            tid = trip["id"]
            headers = {"X-Trip-Key": trip["owner_key"]}
            base = f"/api/ui/trips/{tid}"
            assert client.get(base).status_code == 404
            checks += 1
            forbidden = client.post(base + "/preview", headers=headers, json={"commands": [{"op": "remove_place", "place_id": "dad-02"}]})
            assert forbidden.status_code == 422
            checks += 1
            body = {"commands": [{"op": "set_mode", "place_id": "dad-02", "mode": "short"}]}
            a = client.post(base + "/preview", headers=headers, json=body)
            b = client.post(base + "/preview", headers=headers, json=body)
            assert a.status_code == b.status_code == 200
            aid, bid = a.json()["feedback_id"], b.json()["feedback_id"]
            assert aid and bid
            assert client.get(base, headers=headers).json()["version"] == 1
            checks += 1
            s = client.post(base + "/shares", headers=headers)
            assert s.status_code == 201
            token = s.json()["token"]
            # Independent client is a parent on a different device: no owner key/cookies.
            with httpx.Client(base_url="http://127.0.0.1:8131", timeout=60) as parent:
                share = parent.get(f"/api/ui/shares/{token}")
                assert share.status_code == 200 and not share.json()["outdated"]
                assert "travelers" not in str(share.json()) and "owner" not in str(share.json())
                assert parent.post(f"/api/ui/shares/{token}/opinions", json={"day": 1, "choice": "힘들 것 같아요"}).status_code == 201
                assert parent.post(f"/api/ui/shares/{token}/opinions", json={"day": 14, "choice": "좋아요"}).status_code == 422
                checks += 1
                assert client.post(base + f"/proposals/{aid}/approve").status_code == 404
                approved = client.post(base + f"/proposals/{aid}/approve", headers=headers)
                assert approved.status_code == 200 and approved.json()["version"] == 2
                assert client.post(base + f"/proposals/{bid}/approve", headers=headers).status_code == 409
                assert client.post(base + f"/proposals/{aid}/approve", headers=headers).status_code == 409
                assert parent.get(f"/api/ui/shares/{token}").json()["outdated"]
                checks += 1
            opinions = client.get(base + "/opinions", headers=headers)
            assert opinions.status_code == 200 and len(opinions.json()) == 1
            oid = opinions.json()[0]["id"]
            assert client.post(base + f"/opinions/{oid}/review", headers=headers).status_code == 200
            assert client.get(base + "/opinions", headers=headers).json()[0]["reviewed"]
            assert client.post(base + f"/proposals/{bid}/reject", headers=headers).status_code == 200
            replace_body = {"request": {"travelers": [profile], "place_ids": ["dad-02", "dad-05"], "days": 2},
                            "conditions": {"name": "UI 검증용", "must_places": ["dad-02"]}, "expected_version": 2}
            replaced = client.put(base, headers=headers, json=replace_body)
            assert replaced.status_code == 200 and replaced.json()["version"] == 3
            assert client.put(base, headers=headers, json=replace_body).status_code == 409
            checks += 1
            assert client.get("/api/ui/md/feedback").status_code == 403
            assert client.get("/api/hitl/feedback").status_code == 403
            assert client.post(base + "/shares", headers={**headers, "Origin": "https://untrusted.example"}).status_code == 403
            checks += 1
            result = client.get("/api/ui/evidence/dad-02/sources")
            assert result.status_code == 200 and result.json()
            checks += 1
        with connect_db() as conn:
            rows = conn.execute("select relname,relrowsecurity from pg_class join pg_namespace n on n.oid=relnamespace "
                                "where n.nspname='public' and relname=any(%s)",
                                (["ui_trips", "ui_proposals", "ui_shares", "ui_opinions"],)).fetchall()
            assert len(rows) == 4 and all(r[1] for r in rows)
            checks += 1
        print(f"Runtime verification passed: {checks} scenario groups (HTTP, independent parent client, actual DB, RLS).")
    finally:
        if tid:
            with connect_db() as conn:
                fids = [r[0] for r in conn.execute("select id from ui_proposals where trip_id=%s", (tid,)).fetchall()]
                conn.execute("delete from ui_opinions where trip_id=%s", (tid,))
                conn.execute("delete from ui_shares where trip_id=%s", (tid,))
                conn.execute("delete from ui_proposals where trip_id=%s", (tid,))
                conn.execute("delete from ui_trips where id=%s", (tid,))
                conn.execute("delete from scoring_feedback where id=any(%s) and actor_id=%s", (fids, tid))
            print("Only this run's test trip, proposals, shares and opinions cleaned up.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Runtime verification failed: " + type(exc).__name__ + (": " + str(exc) if isinstance(exc, AssertionError) else ""))
        raise SystemExit(1) from None
