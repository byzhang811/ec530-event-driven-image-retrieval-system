from retrieval_system.contracts import Event
from retrieval_system.system import RetrievalSystem


def _image_submitted_event(event_id: str, image_id: str) -> Event:
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


def test_end_to_end_upload_and_query_flow() -> None:
    system = RetrievalSystem()

    system.submit_image(image_id="img_alpha", path="images/img_alpha.jpg")
    doc = system.document_db_service.get_document("img_alpha")
    assert doc is not None
    assert len(doc["objects"]) >= 1
    assert system.vector_index_service.count() >= 1

    result = system.search_image(image_id="img_alpha", top_k=3)
    assert result is not None
    assert len(result["results"]) >= 1
    assert result["results"][0]["metadata"]["image_id"] == "img_alpha"


def test_duplicate_events_do_not_create_duplicate_state() -> None:
    system = RetrievalSystem()
    event = _image_submitted_event(event_id="evt_dup", image_id="img_dup")

    system.bus.publish(event)
    first_doc_count = system.document_db_service.count()
    first_vector_count = system.vector_index_service.count()

    system.bus.publish(event)
    second_doc_count = system.document_db_service.count()
    second_vector_count = system.vector_index_service.count()

    assert first_doc_count == 1
    assert second_doc_count == 1
    assert second_vector_count == first_vector_count


def test_annotation_correction_updates_document_review() -> None:
    system = RetrievalSystem()
    system.submit_image(image_id="img_fix", path="images/img_fix.jpg")

    system.correct_annotation("img_fix", notes=["car -> truck on 2nd pass"])
    doc = system.document_db_service.get_document("img_fix")
    assert doc is not None
    assert doc["review"]["status"] == "corrected"
    assert "car -> truck on 2nd pass" in doc["review"]["notes"]
