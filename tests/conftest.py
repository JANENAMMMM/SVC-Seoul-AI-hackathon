from pathlib import Path

import pytest

from src.schema.trip import Trip

FIXTURE = Path(__file__).parent / "fixtures" / "trip_danang_demo.json"


@pytest.fixture
def demo_trip() -> Trip:
    return Trip.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
