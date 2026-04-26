from pathlib import Path
from unittest.mock import Mock

from retrieval_system.event_generator import EventGenerator


def test_deterministic_generator_reproducible() -> None:
    gen_a = EventGenerator(seed=11)
    gen_b = EventGenerator(seed=11)

    events_a = [event.to_dict() for event in gen_a.generate_image_submitted_events(3)]
    events_b = [event.to_dict() for event in gen_b.generate_image_submitted_events(3)]

    assert events_a == events_b


def test_replay_mode_from_sample_dataset() -> None:
    data_path = Path(__file__).resolve().parents[1] / "data" / "sample_events.jsonl"
    events = EventGenerator.replay_from_jsonl(data_path)

    assert len(events) == 3
    assert events[0].topic == "image.submitted"
    assert events[0].event_id == "evt_1042"


def test_generator_publish_can_be_mocked_without_live_broker() -> None:
    generator = EventGenerator(seed=21)
    events = generator.generate_image_submitted_events(2)

    mock_bus = Mock()
    EventGenerator.publish(events, mock_bus)

    assert mock_bus.publish.call_count == 2
