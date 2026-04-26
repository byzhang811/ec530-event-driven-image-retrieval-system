from retrieval_system.bus import InMemoryEventBus
from retrieval_system.contracts import Event
from retrieval_system.system import RetrievalSystem
from retrieval_system.topics import IMAGE_SUBMITTED


def _build_image_event(event_id: str, image_id: str) -> Event:
    return Event.from_dict(
        {
            "type": "publish",
            "topic": "image.submitted",
            "event_id": event_id,
            "payload": {
                "image_id": image_id,
                "path": f"images/{image_id}.jpg",
                "source": "camera_A",
                "timestamp": "2026-04-07T14:33:00Z",
            },
            "timestamp": "2026-04-07T14:33:00Z",
        }
    )


def test_delayed_delivery_converges_after_ticks() -> None:
    bus = InMemoryEventBus()
    system = RetrievalSystem(bus=bus)
    delayed_event = _build_image_event(event_id="evt_delayed", image_id="img_delayed")

    bus.publish(delayed_event, delay_steps=2)
    assert system.document_db_service.count() == 0

    bus.tick(steps=1)
    assert system.document_db_service.count() == 0

    bus.tick(steps=1)
    assert system.document_db_service.count() == 1
    assert system.vector_index_service.count() >= 1


def test_subscriber_downtime_and_replay() -> None:
    bus = InMemoryEventBus()
    system = RetrievalSystem(bus=bus)
    event = _build_image_event(event_id="evt_replay", image_id="img_replay")

    bus.pause_subscription(system.inference_service.subscription_token)
    bus.publish(event)
    assert system.document_db_service.count() == 0

    bus.resume_subscription(system.inference_service.subscription_token)
    bus.publish(event)
    assert system.document_db_service.count() == 1


def test_dropped_message_and_manual_replay() -> None:
    bus = InMemoryEventBus()
    system = RetrievalSystem(bus=bus)
    event = _build_image_event(event_id="evt_dropped", image_id="img_dropped")

    bus.set_topic_drop(IMAGE_SUBMITTED, enabled=True)
    bus.publish(event)
    assert system.document_db_service.count() == 0

    bus.set_topic_drop(IMAGE_SUBMITTED, enabled=False)
    bus.publish(event)
    assert system.document_db_service.count() == 1


def test_malformed_event_is_logged_not_crash() -> None:
    bus = InMemoryEventBus()
    system = RetrievalSystem(bus=bus)

    accepted = bus.publish_raw(
        {
            "type": "publish",
            "topic": "image.submitted",
            "event_id": "",
            "payload": {},
            "timestamp": "2026-04-07T14:33:00Z",
        }
    )

    assert accepted is False
    assert len(bus.rejected_events) == 1
    assert system.document_db_service.count() == 0


def test_query_reflects_current_processed_state() -> None:
    bus = InMemoryEventBus()
    system = RetrievalSystem(bus=bus)
    delayed_event = _build_image_event(event_id="evt_for_query", image_id="img_query_state")

    bus.publish(delayed_event, delay_steps=1)
    early_result = system.search_text("truck", top_k=3)
    assert early_result is not None
    assert early_result["results"] == []

    bus.tick(steps=1)
    converged_result = system.search_text("truck", top_k=3)
    assert converged_result is not None
    assert len(converged_result["results"]) >= 1
