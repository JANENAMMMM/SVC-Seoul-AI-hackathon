"""Owned trip, share and MD interfaces for the redesigned UI. Never returns credentials."""
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from src.database import connect_db
from src.planner.schema import EditCommand, Itinerary, PlanRequest
from src.planner.engine import build_itinerary
from src.planner.sources import load_places
from src.scoring import hitl
from src.scoring.display import mode_view
from src.scoring.provenance import explanations, snapshot_runs
from src.scoring.verify import DIMS, WEIGHTS, grade_display
from src.scoring.visit_modes import load_modes

router = APIRouter(prefix="/api/ui", tags=["redesign"])
ROOT = Path(__file__).resolve().parents[1]
SESSIONS: dict[str, float] = {}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def connection():
    try:
        with connect_db() as conn:
            yield conn
    except (psycopg.Error, RuntimeError):
        raise HTTPException(503, "저장소에 연결할 수 없습니다. 서버 설정과 UI 마이그레이션을 확인하세요.") from None


def md_allowed(request: Request) -> bool:
    token = request.cookies.get("bangeoreum_md", "")
    return bool(token and SESSIONS.get(digest(token), 0) > time.time())


def require_md(request: Request):
    if not md_allowed(request):
        raise HTTPException(403, "운영자 로그인이 필요합니다.")


class Login(BaseModel):
    token: str = Field(min_length=1, max_length=512)


@router.post("/md/session")
def login(body: Login, request: Request, response: Response):
    expected = os.getenv("HITL_MD_TOKEN", "")
    if not expected or not hmac.compare_digest(body.token, expected):
        raise HTTPException(403, "운영자 인증을 확인하세요.")
    now = time.time()
    for key, expiry in list(SESSIONS.items()):
        if expiry <= now:
            del SESSIONS[key]
    token = secrets.token_urlsafe(32)
    SESSIONS[digest(token)] = now + 8 * 3600
    response.set_cookie("bangeoreum_md", token, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", max_age=8 * 3600, path="/api")
    return {"authenticated": True}


@router.delete("/md/session")
def logout(request: Request, response: Response):
    SESSIONS.pop(digest(request.cookies.get("bangeoreum_md", "")), None)
    response.delete_cookie("bangeoreum_md", path="/api")
    return {"authenticated": False}


def evidence_detail(pid: str):
    catalog = load_modes()
    if pid not in catalog:
        raise HTTPException(404, "관광지를 찾을 수 없습니다.")
    runs = snapshot_runs(pid, ROOT / "data/scoring/judge/v2")
    score = read_json(ROOT / "data/scoring/scores_v2.json", {}).get(pid)
    reasons, issue = {}, None
    try:
        if score:
            reasons = explanations(score, runs)
    except ValueError:
        issue = "현재 점수와 정확히 일치하는 검증 실행을 찾지 못했습니다."
    climate = read_json(ROOT / "data/scoring/derived/climate_danang.json", {})
    dimensions = []
    for dim in DIMS:
        source = reasons.get(dim, {})
        dimensions.append({"dimension": dim, "weight": WEIGHTS[dim],
                           "score": catalog[pid]["modes"]["standard"]["dimensions"][dim]["score"],
                           "rationale": source.get("rationale"), "evidence_ids": source.get("evidence_ids", []),
                           "lower_conditions": source.get("lower_conditions", []),
                           "upper_conditions": source.get("upper_conditions", []),
                           "run_id": source.get("run_id")})
    return {"place_id": pid, **catalog[pid], "dimensions": dimensions,
            "modes": {key: {**value, **mode_view(value)} for key, value in catalog[pid]["modes"].items()},
            "verification": {"runs": len(runs), "valid": sum(all(r["report"].get(d, {}).get("valid", False) for d in DIMS) for r in runs),
                             "matched_dimensions": len(reasons), "issue": issue,
                             "method": "유효 반복 결과의 medoid 집계"},
            "climate": climate, "forecast": {"connected": False},
            "notice": "인용·수치 검증 결과이며, 부모님의 실제 체감 검증을 뜻하지 않습니다."}


@router.get("/catalog")
def catalog():
    return [{"place_id": p.id, "name_ko": p.name, "lat": p.lat, "lng": p.lng, "status": p.status,
             "modes": {key: {**value, **mode_view(value)} for key, value in p.modes.items()}}
            for p in load_places().values()]


@router.get("/evidence/{pid}")
def evidence(pid: str):
    return evidence_detail(pid)


def source_records(conn, pid: str):
    detail = evidence_detail(pid)
    ids = set()
    for d in detail["dimensions"]:
        ids.update(d["evidence_ids"])
        for condition in d["lower_conditions"] + d["upper_conditions"]:
            ids.update(condition.get("evidence_ids", []))
    rows = conn.execute("select id,source,source_url,text,caveat,value,unit from scoring_evidence where id=any(%s)", (list(ids),)).fetchall()
    records = [dict(zip(("id", "source", "url", "text", "caveat", "value", "unit"), row)) for row in rows]
    web = conn.execute("select url,title,excerpt from scoring_web_cache where place_id=%s", (pid,)).fetchall()
    for url, title, excerpt in web:
        if url in ids or any(url in str(i) for i in ids):
            records.append({"id": url, "source": "웹 검색", "url": url, "text": title, "caveat": None})
    return records


@router.get("/evidence/{pid}/sources")
def sources(pid: str, conn=Depends(connection)):
    return source_records(conn, pid)


@router.get("/md/evaluation", dependencies=[Depends(require_md)])
def evaluation():
    entries = [evidence_detail(pid) for pid in load_modes()]
    return {"places": entries, "total": len(entries),
            "review_required": sum(p["status"] != "ok" for p in entries),
            "matched_dimensions": sum(p["verification"]["matched_dimensions"] for p in entries),
            "runs": sum(p["verification"]["runs"] for p in entries)}


class Conditions(BaseModel):
    name: str = Field(default="엄마", min_length=1, max_length=20)
    avoid_tags: list[Literal["계단·오르막", "긴 보행", "더위 노출", "혼잡"]] = Field(default_factory=list)
    must_places: list[str] = Field(default_factory=list, max_length=15)


class NewTrip(BaseModel):
    request: PlanRequest
    conditions: Conditions
    expected_version: int | None = Field(default=None, ge=1)


def assert_conditions(itinerary: Itinerary, conditions: dict):
    scheduled = {s.place_id for d in itinerary.days for s in d.stops if s.type == "attraction"}
    if set(conditions.get("must_places", [])) - scheduled:
        raise HTTPException(422, "꼭 가고 싶은 장소를 모두 배치할 수 없습니다. 날짜나 조건을 바꿔주세요.")


def owned(conn, trip_id: str, key: str):
    row = conn.execute("select owner_hash, itinerary, conditions, version from public.ui_trips where id=%s",
                       (trip_id,)).fetchone()
    if not row or not key or not hmac.compare_digest(row[0], digest(key)):
        raise HTTPException(404, "여행을 찾을 수 없거나 접근 권한이 없습니다.")
    return row


@router.post("/trips", status_code=201)
def new_trip(body: NewTrip, conn=Depends(connection)):
    try:
        itinerary = build_itinerary(body.request)
    except ValueError:
        raise HTTPException(422, "조건에 맞는 일정을 만들 수 없습니다.") from None
    conditions = body.conditions.model_dump()
    assert_conditions(itinerary, conditions)
    trip_id, key = secrets.token_urlsafe(18), secrets.token_urlsafe(32)
    conn.execute("insert into public.ui_trips(id, owner_hash, itinerary, conditions) values (%s,%s,%s,%s)",
                 (trip_id, digest(key), Jsonb(itinerary.model_dump(mode="json")), Jsonb(conditions)))
    return {"id": trip_id, "owner_key": key, "itinerary": itinerary, "version": 1}


@router.get("/trips/{trip_id}")
def trip(trip_id: str, x_trip_key: str = Header(default=""), conn=Depends(connection)):
    row = owned(conn, trip_id, x_trip_key)
    return {"id": trip_id, "itinerary": row[1], "conditions": row[2], "version": row[3]}


@router.put("/trips/{trip_id}")
def replace_conditions(trip_id: str, body: NewTrip, x_trip_key: str = Header(default=""), conn=Depends(connection)):
    owned(conn, trip_id, x_trip_key)
    row = conn.execute("select version from public.ui_trips where id=%s for update", (trip_id,)).fetchone()
    if body.expected_version != row[0]:
        raise HTTPException(409, "조건이 변경된 새 일정이 있습니다. 다시 확인하세요.")
    try:
        itinerary = build_itinerary(body.request)
    except ValueError:
        raise HTTPException(422, "조건에 맞는 일정을 만들 수 없습니다.") from None
    conditions = body.conditions.model_dump()
    assert_conditions(itinerary, conditions)
    conn.execute("update public.ui_trips set itinerary=%s,conditions=%s,version=version+1 where id=%s",
                 (Jsonb(itinerary.model_dump(mode="json")), Jsonb(conditions), trip_id))
    return {"id": trip_id, "itinerary": itinerary, "version": row[0] + 1}


class Preview(BaseModel):
    commands: list[EditCommand] = Field(default_factory=list, max_length=20)
    feedback: str | None = Field(default=None, max_length=1000)


@router.post("/trips/{trip_id}/preview")
def preview(trip_id: str, body: Preview, x_trip_key: str = Header(default=""), conn=Depends(connection)):
    row = owned(conn, trip_id, x_trip_key)
    from src.planner.feedback import FeedbackInterpreter
    interpreter = None
    if body.feedback and not body.commands and FeedbackInterpreter.available():
        from api.hitl import PARSE_LIMIT
        if not PARSE_LIMIT.allow(trip_id):
            raise HTTPException(429, "조정 요청 한도에 도달했습니다.")
        interpreter = FeedbackInterpreter()
    out = hitl.propose_itinerary(conn, Itinerary.model_validate(row[1]), body.commands, body.feedback,
                                "child", trip_id, interpreter=interpreter)
    response, fid = out["response"], out["feedback_id"]
    if fid:
        assert_conditions(response.itinerary, row[2])
        conn.execute("insert into public.ui_proposals(id, trip_id, base_version) values (%s,%s,%s)",
                     (fid, trip_id, row[3]))
    return {"feedback_id": fid, "proposal": response}


@router.post("/trips/{trip_id}/proposals/{fid}/{action}")
def decide(trip_id: str, fid: str, action: Literal["approve", "reject"],
           x_trip_key: str = Header(default=""), conn=Depends(connection)):
    owned(conn, trip_id, x_trip_key)
    # Serialize decisions and prevent stale proposals replacing newer confirmed itineraries.
    row = conn.execute("select version from public.ui_trips where id=%s for update", (trip_id,)).fetchone()
    p = conn.execute("select base_version from public.ui_proposals where id=%s and trip_id=%s", (fid, trip_id)).fetchone()
    if not p:
        raise HTTPException(404, "변경안을 찾을 수 없습니다.")
    try:
        if action == "reject":
            return hitl.reject(conn, fid, trip_id)
        if p[0] != row[0]:
            raise HTTPException(409, "새 일정이 있습니다. 다시 조정해주세요.")
        updated = hitl.approve_itinerary(conn, fid, trip_id)
        conn.execute("update public.ui_trips set itinerary=%s, version=version+1 where id=%s",
                     (Jsonb(updated.model_dump(mode="json")), trip_id))
        return {"itinerary": updated, "version": row[0] + 1}
    except ValueError:
        raise HTTPException(409, "이미 처리되었거나 승인할 수 없는 변경안입니다.") from None


def share_snapshot(it: dict, name: str):
    catalog = load_modes()
    days = []
    for day in it["days"]:
        stops = []
        for s in day["stops"]:
            public = {k: s.get(k) for k in ("type", "start", "end", "name", "mode_name", "transport", "minutes")}
            if s.get("place_id") in catalog and s.get("mode") in catalog[s["place_id"]]["modes"]:
                public.update(mode_view(catalog[s["place_id"]]["modes"][s["mode"]]))
            if s.get("restaurant"):
                public["name"] = s["restaurant"]["name"]
            stops.append(public)
        days.append({"day": day["day"], "stops": stops, "total_walk_min": day["total_walk_min"],
                     "grade": grade_display(day.get("difficulty")),
                     "rests": sum(s["type"] == "rest" for s in day["stops"])})
    return {"name": name, "start_date": it.get("request", {}).get("start_date"), "days": days}


@router.post("/trips/{trip_id}/shares", status_code=201)
def create_share(trip_id: str, x_trip_key: str = Header(default=""), conn=Depends(connection)):
    row = owned(conn, trip_id, x_trip_key)
    token = secrets.token_urlsafe(32)
    snapshot = share_snapshot(row[1], row[2]["name"])
    conn.execute("insert into public.ui_shares(token_hash,trip_id,version,snapshot) values (%s,%s,%s,%s)",
                 (digest(token), trip_id, row[3], Jsonb(snapshot)))
    return {"token": token, "snapshot": snapshot, "version": row[3]}


@router.get("/shares/{token}")
def shared(token: str, conn=Depends(connection)):
    row = conn.execute("select s.snapshot,s.version,t.version from public.ui_shares s join public.ui_trips t on t.id=s.trip_id "
                       "where s.token_hash=%s", (digest(token),)).fetchone()
    if not row:
        raise HTTPException(404, "공유 일정을 찾을 수 없습니다.")
    return {"snapshot": row[0], "version": row[1], "outdated": row[1] != row[2]}


class Opinion(BaseModel):
    day: int = Field(ge=1, le=14)
    choice: Literal["좋아요", "힘들 것 같아요", "여기는 꼭 가고 싶어요"]


OPINION_LIMIT = hitl.RateLimiter(max_calls=30, window_s=3600)


@router.post("/shares/{token}/opinions", status_code=201)
def opinion(token: str, body: Opinion, conn=Depends(connection)):
    row = conn.execute("select trip_id,version,snapshot from public.ui_shares where token_hash=%s", (digest(token),)).fetchone()
    if not row:
        raise HTTPException(404, "공유 일정을 찾을 수 없습니다.")
    if body.day not in [d["day"] for d in row[2]["days"]]:
        raise HTTPException(422, "공유 일정에 없는 날짜입니다.")
    if not OPINION_LIMIT.allow(digest(token)):
        raise HTTPException(429, "의견은 잠시 후 다시 남겨주세요.")
    conn.execute("insert into public.ui_opinions(trip_id,share_hash,version,day,choice) values (%s,%s,%s,%s,%s)",
                 (row[0], digest(token), row[1], body.day, body.choice))
    return {"received": True, "message": "자녀에게 의견을 전달했어요. 일정은 아직 바뀌지 않았어요."}


@router.get("/trips/{trip_id}/opinions")
def opinions(trip_id: str, x_trip_key: str = Header(default=""), conn=Depends(connection)):
    owned(conn, trip_id, x_trip_key)
    rows = conn.execute("select id,day,choice,version,created_at,reviewed from public.ui_opinions where trip_id=%s order by created_at desc limit 100",
                        (trip_id,)).fetchall()
    return [dict(zip(("id", "day", "choice", "version", "created_at", "reviewed"), r)) for r in rows]


@router.post("/trips/{trip_id}/opinions/{oid}/review")
def review_opinion(trip_id: str, oid: int, x_trip_key: str = Header(default=""), conn=Depends(connection)):
    owned(conn, trip_id, x_trip_key)
    conn.execute("update public.ui_opinions set reviewed=true where id=%s and trip_id=%s", (oid, trip_id))
    return {"reviewed": True}


@router.get("/md/feedback", dependencies=[Depends(require_md)])
def feedback(status: str | None = None, conn=Depends(connection)):
    rows = conn.execute("select id,place_id,status,raw_text,parsed,created_at from scoring_feedback where target='score' "
                        "and (%s::text is null or status=%s) order by created_at desc limit 100", (status, status)).fetchall()
    return [dict(zip(("id", "place_id", "status", "raw_text", "parsed", "created_at"), r)) for r in rows]


@router.get("/md/feedback/{fid}", dependencies=[Depends(require_md)])
def feedback_detail(fid: str, conn=Depends(connection)):
    try:
        fb = hitl.get_feedback(conn, fid)
        if fb["target"] != "score":
            raise KeyError(fid)
        cat = load_modes()
        places = set((fb.get("before_json") or {}).keys())
        saved_view = (fb.get("parsed") or {}).get("ui_before_view")
        fb["before_view"] = saved_view or {
            pid: {m: {"grade": grade_display(value), "cautions": None}
                  for m, value in (fb["before_json"][pid] or {}).items()}
            for pid in places if pid in cat}
        fb["after_view"] = {pid: {"view": hitl._aggregate_view(r["aggregate"]), "human_review": r.get("human_review", {}),
                                  "human_cited": r.get("human_cited", [])}
                            for pid, r in (fb.get("after_json") or {}).get("results", {}).items()}
        return fb
    except KeyError:
        raise HTTPException(404, "검수 건을 찾을 수 없습니다.") from None


class MdText(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/md/feedback", dependencies=[Depends(require_md)])
def md_propose(body: MdText, conn=Depends(connection)):
    from api.hitl import PARSE_LIMIT
    if not PARSE_LIMIT.allow("ui-md"):
        raise HTTPException(429, "해석 호출 한도에 도달했습니다.")
    result = hitl.propose_score(conn, body.text, "ui-md")
    if result.get("feedback_id"):
        conn.execute("update scoring_feedback set parsed=jsonb_set(parsed,'{ui_before_view}',%s) where id=%s",
                     (Jsonb(result["before_view"]), result["feedback_id"]))
    return result


@router.post("/md/feedback/{fid}/{action}", dependencies=[Depends(require_md)])
def md_decide(fid: str, action: Literal["rejudge", "approve", "reject"], conn=Depends(connection)):
    from api.hitl import REJUDGE_LIMIT
    try:
        fb = hitl.get_feedback(conn, fid)
        if fb["target"] != "score":
            raise KeyError(fid)
        if action == "rejudge":
            if not REJUDGE_LIMIT.allow("ui-md"):
                raise HTTPException(429, "하루 재채점 한도에 도달했습니다.")
            return hitl.rejudge(conn, fid)
        if action == "approve":
            current = load_modes()
            if any(pid not in current or hitl._mode_scores(current, pid) != old
                   for pid, old in (fb.get("before_json") or {}).items()):
                raise HTTPException(409, "공개 평가가 이미 바뀌었습니다. 최신 근거로 다시 제안하세요.")
            return hitl.approve_score(conn, fid, "ui-md")
        return hitl.reject(conn, fid, "ui-md")
    except KeyError:
        raise HTTPException(404, "검수 건을 찾을 수 없습니다.") from None
    except ValueError:
        raise HTTPException(409, "현재 상태에서 처리할 수 없습니다. 목록을 새로고침하세요.") from None
