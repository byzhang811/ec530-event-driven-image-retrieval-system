"""Data stores owned by dedicated services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .vector_math import cosine_similarity


@dataclass
class VectorRecord:
    vector_id: str
    vector: list[float]
    metadata: dict[str, Any]


class DocumentStore:
    """JSON-like document store for variable annotation records."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}
        self._processed_events: set[str] = set()

    def upsert_from_inference(
        self,
        *,
        event_id: str,
        image_id: str,
        camera: str,
        objects: list[dict[str, Any]],
        model_version: str,
        timestamp: str,
    ) -> bool:
        if event_id in self._processed_events:
            return False

        document = self._records.get(
            image_id,
            {
                "image_id": image_id,
                "camera": camera,
                "objects": [],
                "review": {"status": "generated", "notes": []},
                "history": [],
            },
        )
        document["camera"] = camera
        document["objects"] = list(objects)
        document["model_version"] = model_version
        document["history"] = list(document.get("history", []))
        document["history"].append({"status": "inference.completed", "at": timestamp})
        self._records[image_id] = document
        self._processed_events.add(event_id)
        return True

    def apply_correction(
        self,
        *,
        event_id: str,
        image_id: str,
        notes: list[str],
        timestamp: str,
    ) -> bool:
        if event_id in self._processed_events:
            return False
        if image_id not in self._records:
            return False

        document = self._records[image_id]
        review = dict(document.get("review", {}))
        review["status"] = "corrected"
        review_notes = list(review.get("notes", []))
        review_notes.extend(notes)
        review["notes"] = review_notes
        document["review"] = review
        document["history"] = list(document.get("history", []))
        document["history"].append({"status": "annotation.corrected", "at": timestamp})
        self._records[image_id] = document
        self._processed_events.add(event_id)
        return True

    def get(self, image_id: str) -> dict[str, Any] | None:
        record = self._records.get(image_id)
        return dict(record) if record else None

    def all(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._records.values()]

    def count(self) -> int:
        return len(self._records)


class VectorIndexStore:
    """Simple vector index abstraction (non-ANN) for simulation."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}
        self._processed_events: set[str] = set()

    def add_embeddings(self, *, event_id: str, embeddings: list[dict[str, Any]]) -> bool:
        if event_id in self._processed_events:
            return False

        for item in embeddings:
            vector_id = str(item["id"])
            vector = [float(v) for v in item["vector"]]
            metadata = dict(item.get("metadata", {}))
            self._records[vector_id] = VectorRecord(
                vector_id=vector_id,
                vector=vector,
                metadata=metadata,
            )

        self._processed_events.add(event_id)
        return True

    def get_vector(self, vector_id: str) -> list[float] | None:
        record = self._records.get(vector_id)
        if record is None:
            return None
        return list(record.vector)

    def query(self, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for record in self._records.values():
            scored.append(
                {
                    "id": record.vector_id,
                    "score": round(cosine_similarity(query_vector, record.vector), 6),
                    "metadata": dict(record.metadata),
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return len(self._records)
