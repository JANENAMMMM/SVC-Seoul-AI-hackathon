"""Read-only score catalog and explicit itinerary evaluation."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.scoring.display import mode_view
from src.scoring.itinerary import evaluate_itinerary
from src.scoring.visit_modes import load_modes


router = APIRouter(prefix="/api/scoring", tags=["scoring"])


class Stop(BaseModel):
    place_id: str
    mode: str
    source_ref: str
    route_note: str


class Itinerary(BaseModel):
    days: list[list[Stop]]


@router.get("/places")
def places():
    catalog = load_modes()
    return [{"place_id": pid, "name_ko": place["name_ko"], "status": place["status"],
             "modes": {key: {"name": mode["name"], "score": mode["score"], **mode_view(mode)}
                       for key, mode in place["modes"].items()}}
            for pid, place in catalog.items()]


@router.get("/places/{place_id}")
def place_detail(place_id: str):
    place = load_modes().get(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="unknown place")
    return {**place, "modes": {key: {**mode, **mode_view(mode)} for key, mode in place["modes"].items()}}


@router.post("/packages/evaluate")
def package_evaluate(itinerary: Itinerary):
    try:
        return evaluate_itinerary(
            [[stop.model_dump() for stop in day] for day in itinerary.days], load_modes())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
