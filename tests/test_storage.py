import pytest

from src.storage import (
    VersionConflict, connect, load_profile, load_trip, save_profile, save_trip,
    save_validation,
)


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "t.db")
    yield c
    c.close()


def test_save_and_load_trip(conn, demo_trip):
    assert load_trip(conn, demo_trip.id) is None
    saved = save_trip(conn, demo_trip)
    assert saved.version == 1
    assert load_trip(conn, demo_trip.id) == saved


def test_version_increments(conn, demo_trip):
    save_trip(conn, demo_trip)
    second = save_trip(conn, demo_trip.model_copy(update={"budget_krw": 3500000}))
    assert second.version == 2
    loaded = load_trip(conn, demo_trip.id)
    assert loaded.version == 2 and loaded.budget_krw == 3500000


def test_version_conflict(conn, demo_trip):
    save_trip(conn, demo_trip)
    save_trip(conn, demo_trip, expected_version=1)
    with pytest.raises(VersionConflict):
        save_trip(conn, demo_trip, expected_version=1)


def test_save_validation_keeps_version(conn, demo_trip):
    saved = save_trip(conn, demo_trip.model_copy(update={"validation": None}))
    report = demo_trip.validation.model_copy(update={"trip_version": saved.version, "baseline": None})
    after = save_validation(conn, demo_trip.id, report)
    assert after.version == saved.version
    assert after.validation.trip_version == after.version  # 최신 판정
    assert after.validation.baseline == report.metrics      # 첫 검증이 기준선


def test_save_validation_keeps_first_baseline(conn, demo_trip):
    saved = save_trip(conn, demo_trip.model_copy(update={"validation": None}))
    first = demo_trip.validation.model_copy(update={"trip_version": saved.version, "baseline": None})
    save_validation(conn, demo_trip.id, first)
    saved2 = save_trip(conn, load_trip(conn, demo_trip.id))  # 일정 수정
    fixed = first.metrics.model_copy(update={"violations": 0})
    second = first.model_copy(update={"trip_version": saved2.version, "metrics": fixed})
    after = save_validation(conn, demo_trip.id, second)
    assert after.validation.baseline.violations == 2 and after.validation.metrics.violations == 0


def test_save_validation_stale(conn, demo_trip):
    save_trip(conn, demo_trip)
    save_trip(conn, demo_trip)  # version 2
    stale = demo_trip.validation.model_copy(update={"trip_version": 1})
    with pytest.raises(VersionConflict):
        save_validation(conn, demo_trip.id, stale)


def test_profiles(conn, demo_trip):
    mom = demo_trip.parents[0]
    save_profile(conn, "parent-mom", mom)
    loaded = load_profile(conn, "parent-mom")
    assert loaded.name == "어머니" and loaded.id == "parent-mom"
    assert load_profile(conn, "nope") is None
