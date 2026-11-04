"""HITL 조정 API(해커톤 단순화 버전): 제안 → (점수는 재채점) → 승인/거절. 설계: docs/scoring-ai/hitl_design.md

- 일정: POST /api/hitl/itinerary/preview → POST /api/hitl/{id}/approve (확정 일정 반환)
- 점수(MD): POST /api/hitl/score/preview → POST /api/hitl/score/{id}/rejudge → POST /api/hitl/{id}/approve
- 공통: POST /api/hitl/{id}/reject, GET /api/hitl/feedback

MD 엔드포인트는 환경변수 HITL_MD_TOKEN이 있으면 X-MD-Token 헤더가 같아야 한다(값은 로그·응답에 남기지 않음).
LLM을 쓰는 엔드포인트는 사용자별 시간당 호출 수를 제한한다(팀 크레딧 보호).
"""
import hmac
import os
from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.planner.feedback import FeedbackInterpreter
from src.planner.schema import EditCommand, Itinerary, RefineResponse
from src.scoring import db, hitl

router = APIRouter(prefix="/api/hitl", tags=["hitl"])
PARSE_LIMIT = hitl.RateLimiter(max_calls=30, window_s=3600)   # Haiku 해석
REJUDGE_LIMIT = hitl.RateLimiter(max_calls=5, window_s=86400)  # Sonnet 재채점 (하루)


def _md_guard(token: Optional[str]):
    expected = os.getenv("HITL_MD_TOKEN")
    if expected and not (token and hmac.compare_digest(token, expected)):
        raise HTTPException(status_code=403, detail="MD 권한이 필요합니다.")


def _limit(limiter, key):
    if not limiter.allow(key or "anonymous"):
        raise HTTPException(status_code=429, detail="호출 한도를 넘었습니다. 잠시 후 다시 시도하세요.")


class ItineraryPreview(BaseModel):
    itinerary: Itinerary
    commands: list[EditCommand] = Field(default_factory=list)
    feedback: Optional[str] = None
    actor_role: Literal["child", "parent"] = "child"
    actor_id: Optional[str] = None


class PreviewResponse(BaseModel):
    feedback_id: Optional[str]
    proposal: RefineResponse


class ScorePreview(BaseModel):
    text: str
    actor_id: Optional[str] = None


class Decision(BaseModel):
    approver: Optional[str] = None


@router.post("/itinerary/preview", response_model=PreviewResponse)
def itinerary_preview(body: ItineraryPreview):
    interpreter = None
    if body.feedback and not body.commands and FeedbackInterpreter.available():
        _limit(PARSE_LIMIT, body.actor_id)
        interpreter = FeedbackInterpreter()
    try:
        with db.connect() as conn:
            out = hitl.propose_itinerary(conn, body.itinerary, body.commands, body.feedback,
                                         body.actor_role, body.actor_id, interpreter=interpreter)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return PreviewResponse(feedback_id=out["feedback_id"], proposal=out["response"])


@router.post("/score/preview")
def score_preview(body: ScorePreview, x_md_token: Optional[str] = Header(default=None)):
    _md_guard(x_md_token)
    _limit(PARSE_LIMIT, body.actor_id)
    with db.connect() as conn:
        return hitl.propose_score(conn, body.text, body.actor_id)


@router.post("/score/{fid}/rejudge")
def score_rejudge(fid: str, body: Decision, x_md_token: Optional[str] = Header(default=None)):
    _md_guard(x_md_token)
    _limit(REJUDGE_LIMIT, body.approver)
    try:
        with db.connect() as conn:
            return hitl.rejudge(conn, fid)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown feedback") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/{fid}/approve")
def approve(fid: str, body: Decision, x_md_token: Optional[str] = Header(default=None)):
    try:
        with db.connect() as conn:
            fb = hitl.get_feedback(conn, fid)
            if fb["target"] == "score":
                _md_guard(x_md_token)
                return hitl.approve_score(conn, fid, body.approver)
            return {"feedback_id": fid, "status": "applied",
                    "itinerary": hitl.approve_itinerary(conn, fid, body.approver)}
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown feedback") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.post("/{fid}/reject")
def reject(fid: str, body: Decision, x_md_token: Optional[str] = Header(default=None)):
    try:
        with db.connect() as conn:
            if hitl.get_feedback(conn, fid)["target"] == "score":
                _md_guard(x_md_token)
            return hitl.reject(conn, fid, body.approver)
    except KeyError:
        raise HTTPException(status_code=404, detail="unknown feedback") from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None


@router.get("/feedback")
def feedback(place_id: Optional[str] = None, limit: int = 50):
    with db.connect() as conn:
        return hitl.history(conn, place_id, min(limit, 200))

