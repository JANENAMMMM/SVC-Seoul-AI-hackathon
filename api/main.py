"""반걸음 FastAPI. 실행: uv run uvicorn api.main:app --reload"""
import os
import sqlite3
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.schema.trip import Trip, ValidationReport
from src.storage import VersionConflict, connect, load_trip, save_trip, save_validation

app = FastAPI(title="반걸음 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@lru_cache
def _conn() -> sqlite3.Connection:
    return connect(os.getenv("BANGEOREUM_DB", "data/bangeoreum.db"))


def get_conn() -> sqlite3.Connection:
    return _conn()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/trips/{trip_id}", response_model=Trip)
def get_trip(trip_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> Trip:
    trip = load_trip(conn, trip_id)
    if trip is None:
        raise HTTPException(404, f"trip {trip_id} not found")
    return trip


@app.put("/api/trips/{trip_id}", response_model=Trip)
def put_trip(
    trip_id: str,
    trip: Trip,
    if_match: int | None = Header(default=None),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Trip:
    """저장 시 version은 서버가 +1 한다 (body의 version 값은 무시).

    If-Match 헤더에 클라이언트가 읽은 version을 주면, 그 사이 다른 탭이 저장했을 때 409.
    """
    if trip.id != trip_id:
        raise HTTPException(400, "path id와 body id가 다릅니다")
    try:
        return save_trip(conn, trip, expected_version=if_match)
    except VersionConflict as e:
        raise HTTPException(409, {"message": str(e), "current_version": e.current})


@app.put("/api/trips/{trip_id}/validation", response_model=Trip)
def put_validation(
    trip_id: str, report: ValidationReport, conn: sqlite3.Connection = Depends(get_conn)
) -> Trip:
    """검증 엔진 전용. version을 올리지 않고, report.trip_version이 현재와 다르면 409."""
    try:
        return save_validation(conn, trip_id, report)
    except KeyError:
        raise HTTPException(404, f"trip {trip_id} not found")
    except VersionConflict as e:
        raise HTTPException(409, {"message": str(e), "current_version": e.current})
