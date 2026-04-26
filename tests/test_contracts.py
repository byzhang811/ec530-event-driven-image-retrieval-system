from retrieval_system.bus import InMemoryEventBus
from retrieval_system.contracts import Event, EventValidationError


def test_event_schema_round_trip() -> None:
    raw = {
        "type": "publish",
        "topic": "image.submitted",
        "event_id": "evt_1042",
        "payload": {
            "image_id": "img_1042",
            "path": "images/street_1042.jpg",
            "source": "camera_A",
            "timestamp": "2026-04-07T14:33:00Z",
        },
        "timestamp": "2026-04-07T14:33:00Z",
    }
    event = Event.from_dict(raw)
    serialized = event.to_dict()

    assert serialized["type"] == "publish"
    assert serialized["topic"] == "image.submitted"
    assert serialized["event_id"] == "evt_1042"
    assert serialized["payload"]["image_id"] == "img_1042"
    assert serialized["timestamp"].endswith("Z")


def test_missing_keys_raise_validation_error() -> None:
    raw = {
        "type": "publish",
        "event_id": "evt_missing",
        "payload": {},
        "timestamp": "2026-04-07T14:33:00Z",
    }
    try:
        Event.from_dict(raw)
    except EventValidationError as exc:
        assert "topic" in str(exc)
    else:
        raise AssertionError("Expected EventValidationError for missing topic")


def test_malformed_event_is_rejected_without_crash() -> None:
    bus = InMemoryEventBus()
    malformed = {
        "type": "publish",
        "topic": "",
        "event_id": "evt_bad",
        "payload": {},
        "timestamp": "2026-04-07T14:33:00Z",
    }
    accepted = bus.publish_raw(malformed)
    assert accepted is False
    assert len(bus.rejected_events) == 1
