"""User-facing view of a 1-10 score: a 3-step grade plus the dimensions that need care.

Why not show the raw 1-10 number: re-scoring the same evidence moves scores by about 1 point,
and the weighted composite only spans 2-6 across our 15 places, so single points are noise.
The grade (하/중/상) survived the v2.1 -> v2.2 re-score for 11/15 places.
Why cautions: the composite is an average, so one hard barrier (e.g. 오행산 stairs) is diluted
by easy dimensions. Any dimension scored >= CAUTION_MIN is surfaced by name instead.
The 1-10 scale itself stays internal (anchored rubric, ranking, itinerary totals).
"""
from src.scoring.verify import DIMS, grade_display

CAUTION_MIN = 7
CAUTION_LABEL = {"climb": "계단·오르막", "walking": "긴 보행", "heat": "더위 노출", "crowd": "혼잡"}


def cautions(dimensions):
    """dimensions: {dim: {"score": int, ...}} (visit-mode shape) -> labels of hard dimensions."""
    return [CAUTION_LABEL[d] for d in DIMS
            if (dimensions.get(d) or {}).get("score") is not None and dimensions[d]["score"] >= CAUTION_MIN]


def mode_view(mode):
    return {"grade": grade_display(mode["score"]), "cautions": cautions(mode["dimensions"])}
