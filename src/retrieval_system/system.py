"""High-level wiring for the event-driven retrieval system."""

from __future__ import annotations

from typing import Any

from .bus import EventBus, InMemoryEventBus
from .services import (
    CLIService,
    DocumentDBService,
    EmbeddingService,
    InferenceService,
    QueryService,
    UploadService,
    VectorIndexService,
)


class RetrievalSystem:
    """Composes services into one event-driven application."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or InMemoryEventBus()

        self.upload_service = UploadService(self.bus)
        self.inference_service = InferenceService(self.bus)
        self.document_db_service = DocumentDBService(self.bus)
        self.embedding_service = EmbeddingService(
            self.bus,
            document_lookup=self.document_db_service.get_document,
        )
        self.vector_index_service = VectorIndexService(self.bus)
        self.query_service = QueryService(self.bus, self.vector_index_service)
        self.cli_service = CLIService(self.bus, self.upload_service)

    def submit_image(self, *, image_id: str, path: str, source: str = "camera_A") -> None:
        self.cli_service.upload(image_id=image_id, path=path, source=source)

    def search_text(self, query: str, top_k: int = 3) -> dict[str, Any] | None:
        query_id = self.cli_service.query_text(query=query, top_k=top_k)
        return self.cli_service.wait_for_query_result(query_id)

    def search_image(self, image_id: str, top_k: int = 3) -> dict[str, Any] | None:
        query_id = self.cli_service.query_image(image_id=image_id, top_k=top_k)
        return self.cli_service.wait_for_query_result(query_id)

    def correct_annotation(self, image_id: str, notes: list[str]) -> None:
        self.cli_service.correct_annotation(image_id=image_id, notes=notes)
