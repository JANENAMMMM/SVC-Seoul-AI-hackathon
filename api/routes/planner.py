"""일정 생성·수정 API. 서버는 상태를 저장하지 않고, 클라이언트가 이전 일정(state 포함)을 다시 보낸다."""

from fastapi import APIRouter, HTTPException

from src.planner.edit import refine
from src.planner.engine import build_itinerary
from src.planner.feedback import FeedbackInterpreter
from src.planner.schema import Itinerary, PlanRequest, RefineRequest, RefineResponse
from src.scoring.hitl import RateLimiter

router = APIRouter(prefix="/api/planner", tags=["planner"])
REFINE_LIMIT = RateLimiter(max_calls=60, window_s=3600)  # 자연어 해석(Haiku) 호출 제한, 서버 전체


@router.post("/plan", response_model=Itinerary)
def plan(request: PlanRequest) -> Itinerary:
    try:
        return build_itinerary(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/refine", response_model=RefineResponse)
def refine_plan(body: RefineRequest) -> RefineResponse:
    try:
        # ANTHROPIC_API_KEY가 있을 때만 자연어 피드백을 명령으로 바꾼다. 없으면 이전처럼 안내만 돌려준다.
        interpreter = FeedbackInterpreter() if FeedbackInterpreter.available() else None
        if interpreter and body.feedback and not body.commands and not REFINE_LIMIT.allow("refine"):
            raise HTTPException(status_code=429, detail="자연어 수정 호출 한도를 넘었습니다. 잠시 후 다시 시도하세요.")
        return refine(body.itinerary, body.commands, body.feedback, interpreter=interpreter)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
