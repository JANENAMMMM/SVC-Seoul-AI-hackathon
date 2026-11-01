from src.schema.trip import Move, Stop, Trip


def test_fixture_validates(demo_trip: Trip):
    assert demo_trip.destination == "다낭"
    assert len(demo_trip.parents) == 2
    assert len(demo_trip.days) == 4  # 3박 4일


def test_items_discriminated(demo_trip: Trip):
    kinds = {type(i) for d in demo_trip.days for i in d.items}
    assert kinds == {Stop, Move}


def test_references_are_consistent(demo_trip: Trip):
    stop_ids = set()
    for day in demo_trip.days:
        for item in day.items:
            if isinstance(item, Stop):
                assert item.place_id in demo_trip.places
                stop_ids.add(item.id)
    for day in demo_trip.days:
        for item in day.items:
            if isinstance(item, Move):
                assert item.from_stop_id in stop_ids and item.to_stop_id in stop_ids
    all_ids = stop_ids | {i.id for d in demo_trip.days for i in d.items}
    for issue in demo_trip.validation.issues:
        assert issue.item_id in all_ids
    assert demo_trip.hotel_place_id in demo_trip.places


def test_two_walking_violations(demo_trip: Trip):
    v = demo_trip.validation
    assert v.metrics.violations == len(v.issues) == 2
    assert {i.rule for i in v.issues} == {"continuous_walk", "stairs"}


def test_roundtrip_json(demo_trip: Trip):
    assert Trip.model_validate_json(demo_trip.model_dump_json()) == demo_trip
