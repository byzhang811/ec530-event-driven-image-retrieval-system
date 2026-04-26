"""Service modules for the event-driven image retrieval pipeline."""

from __future__ import annotations

import hashlib
import random
import time
from typing import Any, Callable

from .bus import EventBus
from .contracts import Event, build_event, new_event_id, to_iso_timestamp, utc_now
from .message_definitions import validate_payload
from .stores import DocumentStore, VectorIndexStore
from .topics import (
    ANNOTATION_CORRECTED,
    ANNOTATION_STORED,
    EMBEDDING_CREATED,
    IMAGE_SUBMITTED,
    INFERENCE_COMPLETED,
    QUERY_COMPLETED,
    QUERY_SUBMITTED,
)
from .vector_math import text_to_vector


class UploadService:
    """Ingress service for image-submission events."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    def submit_image(
        self,
        *,
        image_id: str,
        path: str,
        source: str = "camera_A",
    ) -> Event:
        event = build_event(
            topic=IMAGE_SUBMITTED,
            event_id=new_event_id("evt_submit"),
            payload={
                "image_id": image_id,
                "path": path,
                "source": source,
                "timestamp": to_iso_timestamp(utc_now()),
            },
        )
        self.bus.publish(event)
        return event


class InferenceService:
    """Consumes image submissions and produces simulated detections."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._seen_events: set[str] = set()
        self.subscription_token = self.bus.subscribe(
            IMAGE_SUBMITTED,
            self._on_image_submitted,
            name="inference-service",
        )

    def _on_image_submitted(self, event: Event) -> None:
        if event.event_id in self._seen_events:
            return
        self._seen_events.add(event.event_id)

        try:
            validate_payload(event.topic, event.payload)
        except Exception:
            return

        image_id = str(event.payload.get("image_id", "")).strip()
        path = str(event.payload.get("path", "")).strip()
        source = str(event.payload.get("source", "unknown")).strip() or "unknown"
        if not image_id or not path:
            return

        objects = self._simulate_detections(image_id=image_id, path=path)
        inference_event = build_event(
            topic=INFERENCE_COMPLETED,
            event_id=f"{event.event_id}.inference",
            payload={
                "image_id": image_id,
                "path": path,
                "source": source,
                "model_version": "sim-v1",
                "objects": objects,
            },
        )
        self.bus.publish(inference_event)

    @staticmethod
    def _simulate_detections(*, image_id: str, path: str) -> list[dict[str, Any]]:
        labels = ["car", "truck", "person", "bicycle", "dog", "cat"]
        seed_hex = hashlib.sha256(f"{image_id}:{path}".encode("utf-8")).hexdigest()[:8]
        rng = random.Random(int(seed_hex, 16))
        count = rng.randint(1, 4)

        detections: list[dict[str, Any]] = []
        for _ in range(count):
            x1 = rng.randint(0, 250)
            y1 = rng.randint(0, 250)
            width = rng.randint(24, 180)
            height = rng.randint(24, 180)
            x2 = x1 + width
            y2 = y1 + height
            detections.append(
                {
                    "label": labels[rng.randint(0, len(labels) - 1)],
                    "bbox": [x1, y1, x2, y2],
                    "conf": round(rng.uniform(0.5, 0.99), 2),
                }
            )
        return detections


class DocumentDBService:
    """Owns annotation documents and publishes annotation lifecycle events."""

    def __init__(self, bus: EventBus, store: DocumentStore | None = None) -> None:
        self.bus = bus
        self.store = store or DocumentStore()
        self.inference_subscription_token = self.bus.subscribe(
            INFERENCE_COMPLETED,
            self._on_inference_completed,
            name="document-db-service[inference]",
        )
        self.correction_subscription_token = self.bus.subscribe(
            ANNOTATION_CORRECTED,
            self._on_annotation_corrected,
            name="document-db-service[correction]",
        )

    def _on_inference_completed(self, event: Event) -> None:
        payload = event.payload
        try:
            validate_payload(event.topic, payload)
        except Exception:
            return
        image_id = str(payload.get("image_id", "")).strip()
        if not image_id:
            return

        stored = self.store.upsert_from_inference(
            event_id=event.event_id,
            image_id=image_id,
            camera=str(payload.get("source", "unknown")),
            objects=list(payload.get("objects", [])),
            model_version=str(payload.get("model_version", "sim-v1")),
            timestamp=to_iso_timestamp(event.timestamp),
        )
        if not stored:
            return

        self.bus.publish(
            build_event(
                topic=ANNOTATION_STORED,
                event_id=f"{event.event_id}.stored",
                payload={
                    "image_id": image_id,
                    "object_count": len(payload.get("objects", [])),
                    "review_status": "generated",
                },
            )
        )

    def _on_annotation_corrected(self, event: Event) -> None:
        payload = event.payload
        try:
            validate_payload(event.topic, payload)
        except Exception:
            return
        image_id = str(payload.get("image_id", "")).strip()
        if not image_id:
            return

        updated = self.store.apply_correction(
            event_id=event.event_id,
            image_id=image_id,
            notes=list(payload.get("notes", [])),
            timestamp=to_iso_timestamp(event.timestamp),
        )
        if not updated:
            return

        self.bus.publish(
            build_event(
                topic=ANNOTATION_STORED,
                event_id=f"{event.event_id}.stored",
                payload={
                    "image_id": image_id,
                    "object_count": len(self.get_document(image_id).get("objects", [])),
                    "review_status": "corrected",
                },
            )
        )

    def get_document(self, image_id: str) -> dict[str, Any] | None:
        return self.store.get(image_id)

    def count(self) -> int:
        return self.store.count()


class EmbeddingService:
    """Builds embeddings from stored annotation documents."""

    def __init__(
        self,
        bus: EventBus,
        *,
        document_lookup: Callable[[str], dict[str, Any] | None],
        dims: int = 16,
    ) -> None:
        self.bus = bus
        self.document_lookup = document_lookup
        self.dims = dims
        self._seen_events: set[str] = set()
        self.subscription_token = self.bus.subscribe(
            ANNOTATION_STORED,
            self._on_annotation_stored,
            name="embedding-service",
        )

    def _on_annotation_stored(self, event: Event) -> None:
        if event.event_id in self._seen_events:
            return
        self._seen_events.add(event.event_id)

        try:
            validate_payload(event.topic, event.payload)
        except Exception:
            return

        image_id = str(event.payload.get("image_id", "")).strip()
        if not image_id:
            return

        document = self.document_lookup(image_id)
        if not document:
            return

        objects = list(document.get("objects", []))
        labels = [str(item.get("label", "unknown")) for item in objects]
        image_text = f"image:{image_id} labels:{' '.join(labels)}"

        embeddings: list[dict[str, Any]] = [
            {
                "id": image_id,
                "vector": text_to_vector(image_text, dims=self.dims),
                "metadata": {"image_id": image_id, "kind": "image"},
            }
        ]
        for idx, obj in enumerate(objects):
            label = str(obj.get("label", "unknown"))
            conf = float(obj.get("conf", 0.0))
            embeddings.append(
                {
                    "id": f"{image_id}#obj{idx}",
                    "vector": text_to_vector(f"{image_id}:{label}:{idx}", dims=self.dims),
                    "metadata": {
                        "image_id": image_id,
                        "kind": "object",
                        "label": label,
                        "conf": conf,
                    },
                }
            )

        self.bus.publish(
            build_event(
                topic=EMBEDDING_CREATED,
                event_id=f"{event.event_id}.embedding",
                payload={"image_id": image_id, "embeddings": embeddings},
            )
        )


class VectorIndexService:
    """Owns vector index state and similarity retrieval."""

    def __init__(self, bus: EventBus, store: VectorIndexStore | None = None) -> None:
        self.bus = bus
        self.store = store or VectorIndexStore()
        self.subscription_token = self.bus.subscribe(
            EMBEDDING_CREATED,
            self._on_embedding_created,
            name="vector-index-service",
        )

    def _on_embedding_created(self, event: Event) -> None:
        try:
            validate_payload(event.topic, event.payload)
        except Exception:
            return
        embeddings = list(event.payload.get("embeddings", []))
        if not embeddings:
            return
        self.store.add_embeddings(event_id=event.event_id, embeddings=embeddings)

    def count(self) -> int:
        return self.store.count()

    def get_vector(self, vector_id: str) -> list[float] | None:
        return self.store.get_vector(vector_id)

    def search(self, query_vector: list[float], top_k: int = 3) -> list[dict[str, Any]]:
        return self.store.query(query_vector=query_vector, top_k=top_k)


class QueryService:
    """Consumes query events and publishes retrieval responses."""

    def __init__(self, bus: EventBus, vector_index: VectorIndexService, dims: int = 16) -> None:
        self.bus = bus
        self.vector_index = vector_index
        self.dims = dims
        self._seen_events: set[str] = set()
        self.subscription_token = self.bus.subscribe(
            QUERY_SUBMITTED,
            self._on_query_submitted,
            name="query-service",
        )

    def _on_query_submitted(self, event: Event) -> None:
        if event.event_id in self._seen_events:
            return
        self._seen_events.add(event.event_id)

        payload = event.payload
        try:
            validate_payload(event.topic, payload)
        except Exception:
            return
        query_id = str(payload.get("query_id", event.event_id))
        query_type = str(payload.get("query_type", "text"))
        top_k = int(payload.get("top_k", 3))

        if query_type == "image":
            image_id = str(payload.get("image_id", ""))
            query_vector = self.vector_index.get_vector(image_id) or text_to_vector(
                f"image:{image_id}",
                dims=self.dims,
            )
            query_text = image_id
        else:
            query_text = str(payload.get("query", ""))
            query_vector = text_to_vector(query_text, dims=self.dims)

        results = self.vector_index.search(query_vector=query_vector, top_k=top_k)
        self.bus.publish(
            build_event(
                topic=QUERY_COMPLETED,
                event_id=f"{event.event_id}.completed",
                payload={
                    "query_id": query_id,
                    "query_type": query_type,
                    "query": query_text,
                    "top_k": top_k,
                    "results": results,
                },
            )
        )


class CLIService:
    """Simulated user-facing entrypoint for uploads and queries."""

    def __init__(self, bus: EventBus, upload_service: UploadService) -> None:
        self.bus = bus
        self.upload_service = upload_service
        self._query_results: dict[str, dict[str, Any]] = {}
        self.subscription_token = self.bus.subscribe(
            QUERY_COMPLETED,
            self._on_query_completed,
            name="cli-service",
        )

    def _on_query_completed(self, event: Event) -> None:
        query_id = str(event.payload.get("query_id", ""))
        if query_id:
            self._query_results[query_id] = dict(event.payload)

    def upload(self, *, image_id: str, path: str, source: str = "camera_A") -> Event:
        return self.upload_service.submit_image(image_id=image_id, path=path, source=source)

    def query_text(self, query: str, top_k: int = 3) -> str:
        query_id = new_event_id("qry")
        self.bus.publish(
            build_event(
                topic=QUERY_SUBMITTED,
                event_id=new_event_id("evt_query"),
                payload={
                    "query_id": query_id,
                    "query_type": "text",
                    "query": query,
                    "top_k": top_k,
                },
            )
        )
        return query_id

    def query_image(self, image_id: str, top_k: int = 3) -> str:
        query_id = new_event_id("qry")
        self.bus.publish(
            build_event(
                topic=QUERY_SUBMITTED,
                event_id=new_event_id("evt_query"),
                payload={
                    "query_id": query_id,
                    "query_type": "image",
                    "image_id": image_id,
                    "top_k": top_k,
                },
            )
        )
        return query_id

    def correct_annotation(self, image_id: str, notes: list[str]) -> Event:
        event = build_event(
            topic=ANNOTATION_CORRECTED,
            event_id=new_event_id("evt_correct"),
            payload={"image_id": image_id, "notes": list(notes)},
        )
        self.bus.publish(event)
        return event

    def get_query_result(self, query_id: str) -> dict[str, Any] | None:
        result = self._query_results.get(query_id)
        return dict(result) if result else None

    def wait_for_query_result(
        self,
        query_id: str,
        timeout_s: float = 2.0,
        poll_interval_s: float = 0.02,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            result = self.get_query_result(query_id)
            if result is not None:
                return result
            time.sleep(poll_interval_s)
        return self.get_query_result(query_id)
