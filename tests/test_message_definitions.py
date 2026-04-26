import pytest

from retrieval_system.message_definitions import (
    MESSAGE_DEFINITIONS,
    MessageDefinitionError,
    validate_payload,
)


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        (
            "image.submitted",
            {
                "image_id": "img_1",
                "path": "images/img_1.jpg",
                "source": "camera_A",
                "timestamp": "2026-04-07T14:33:00Z",
            },
        ),
        (
            "inference.completed",
            {
                "image_id": "img_1",
                "path": "images/img_1.jpg",
                "source": "camera_A",
                "model_version": "sim-v1",
                "objects": [],
            },
        ),
        (
            "annotation.stored",
            {"image_id": "img_1", "object_count": 0, "review_status": "generated"},
        ),
        (
            "embedding.created",
            {"image_id": "img_1", "embeddings": [{"id": "img_1", "vector": [0.1]}]},
        ),
        ("annotation.corrected", {"image_id": "img_1", "notes": ["car -> truck"]}),
        (
            "query.submitted",
            {"query_id": "q_1", "query_type": "text", "top_k": 3, "query": "car"},
        ),
        (
            "query.completed",
            {
                "query_id": "q_1",
                "query_type": "text",
                "query": "car",
                "top_k": 3,
                "results": [],
            },
        ),
    ],
)
def test_all_topic_payload_examples_validate(topic: str, payload: dict) -> None:
    validate_payload(topic, payload)


def test_each_topic_has_publish_and_subscribe_definition() -> None:
    for topic, definition in MESSAGE_DEFINITIONS.items():
        assert definition.topic == topic
        assert definition.publisher
        assert definition.subscribers
        assert definition.required_payload_fields


def test_missing_required_payload_fields_raise_error() -> None:
    with pytest.raises(MessageDefinitionError):
        validate_payload("query.submitted", {"query_id": "q_1"})
