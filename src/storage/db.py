"""SQLite 저장소. trips(id, version, data JSON), profiles(id, data JSON).

버전 규칙: save_trip은 저장된 버전 + 1로 저장한다 (신규면 1).
expected_version을 주면 저장된 버전과 다를 때 VersionConflict — 탭끼리 덮어쓰기 방지.
"""
import sqlite3
from pathlib import Path

from src.schema.trip import ParentProfile, Trip, ValidationReport

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id      TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    data    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profiles (
    id   TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
"""


class VersionConflict(Exception):
    def __init__(self, current: int, expected: int):
        super().__init__(f"version conflict: stored={current}, expected={expected}")
        self.current = current
        self.expected = expected


def connect(path: str | Path) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def load_trip(conn: sqlite3.Connection, trip_id: str) -> Trip | None:
    row = conn.execute("SELECT data FROM trips WHERE id = ?", (trip_id,)).fetchone()
    return Trip.model_validate_json(row[0]) if row else None


def save_trip(
    conn: sqlite3.Connection, trip: Trip, expected_version: int | None = None
) -> Trip:
    """저장하고 version이 갱신된 Trip을 돌려준다."""
    with conn:  # 트랜잭션
        row = conn.execute("SELECT version FROM trips WHERE id = ?", (trip.id,)).fetchone()
        current = row[0] if row else 0
        if expected_version is not None and expected_version != current:
            raise VersionConflict(current, expected_version)
        saved = trip.model_copy(update={"version": current + 1})
        conn.execute(
            "INSERT INTO trips (id, version, data) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET version = excluded.version, data = excluded.data",
            (saved.id, saved.version, saved.model_dump_json()),
        )
    return saved


def save_validation(conn: sqlite3.Connection, trip_id: str, report: ValidationReport) -> Trip:
    """검증 결과만 저장. version을 올리지 않는다.

    report.trip_version이 저장된 version과 다르면(그 사이 일정이 바뀜) VersionConflict —
    낡은 검증 결과가 최신 일정에 붙는 것을 막는다.
    """
    with conn:
        row = conn.execute("SELECT version, data FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if row is None:
            raise KeyError(trip_id)
        if report.trip_version != row[0]:
            raise VersionConflict(row[0], report.trip_version)
        trip = Trip.model_validate_json(row[1])
        if report.baseline is None:  # 첫 검증 지표를 보정 전 기준으로 유지
            prev = trip.validation
            baseline = prev.baseline if prev and prev.baseline else (prev.metrics if prev else report.metrics)
            report = report.model_copy(update={"baseline": baseline})
        trip = trip.model_copy(update={"validation": report})
        conn.execute("UPDATE trips SET data = ? WHERE id = ?", (trip.model_dump_json(), trip_id))
    return trip


def load_profile(conn: sqlite3.Connection, profile_id: str) -> ParentProfile | None:
    row = conn.execute("SELECT data FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return ParentProfile.model_validate_json(row[0]) if row else None


def save_profile(conn: sqlite3.Connection, profile_id: str, profile: ParentProfile) -> ParentProfile:
    saved = profile.model_copy(update={"id": profile_id})
    with conn:
        conn.execute(
            "INSERT INTO profiles (id, data) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (profile_id, saved.model_dump_json()),
        )
    return saved
