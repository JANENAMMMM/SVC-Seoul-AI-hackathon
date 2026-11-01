import pytest

from src.storage import (
    VersionConflict, connect, load_profile, load_trip, save_profile, save_trip,
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


def test_profiles(conn, demo_trip):
    mom = demo_trip.parents[0]
    save_profile(conn, "parent-mom", mom)
    loaded = load_profile(conn, "parent-mom")
    assert loaded.name == "어머니" and loaded.id == "parent-mom"
    assert load_profile(conn, "nope") is None
