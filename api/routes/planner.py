"""일정 생성·수정 API. 서버는 상태를 저장하지 않고, 클라이언트가 이전 일정(state 포함)을 다시 보낸다."""

from fastapi import APIRouter, HTTPException

from src.planner.edit import refine
from src.planner.engine import build_itinerary
from src.planner.schema import Itinerary, PlanRequest, RefineRequest, RefineResponse

router = APIRouter(prefix="/api/planner", tags=["planner"])


@router.post("/plan", response_model=Itinerary)
def plan(request: PlanRequest) -> Itinerary:
    try:
        return build_itinerary(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/refine", response_model=RefineResponse)
def refine_plan(body: RefineRequest) -> RefineResponse:
    try:
        return refine(body.itinerary, body.commands, body.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
