# Architecture Presentation Flow (With Code Display Cues)

> Target length: 5-6 minutes  
> Goal: explain architecture while showing the exact code locations live.

## Demo Setup Before Recording

1. Open project root folder in your editor.
2. Keep terminal ready in project root.
3. Pre-open these tabs:
- `src/retrieval_system/system.py`
- `src/retrieval_system/services.py`
- `src/retrieval_system/topics.py`
- `src/retrieval_system/message_definitions.py`
- `src/retrieval_system/contracts.py`
- `src/retrieval_system/bus.py`
- `src/retrieval_system/stores.py`
- `tests/test_pipeline.py`
- `tests/test_failures.py`
- `README.md`

## Minute-by-Minute Script + What to Show

## 0:00 - 0:30 | Project Goal

Say:
"This project is an event-driven image annotation and retrieval system.  
The focus is architecture, messaging, and testability, not model training."

Show on screen:
- Project tree root
- `README.md`

Code location:
- `README.md`

## 0:30 - 1:20 | High-Level Wiring

Say:
"I first wire all services in one place, so the architecture is easy to inspect.  
The system composes Upload, Inference, DocumentDB, Embedding, VectorIndex, Query, and CLI services."

Show on screen:
- `RetrievalSystem` class and constructor wiring

Code location:
- `src/retrieval_system/system.py`

## 1:20 - 2:20 | Service Responsibilities and Event Flow

Say:
"Each service listens and publishes events.  
The upload path is image.submitted -> inference.completed -> annotation.stored -> embedding.created.  
Query path is query.submitted -> query.completed."

Show on screen:
- `UploadService.submit_image`
- `InferenceService._on_image_submitted`
- `DocumentDBService._on_inference_completed`
- `EmbeddingService._on_annotation_stored`
- `QueryService._on_query_submitted`

Code location:
- `src/retrieval_system/services.py`

## 2:20 - 2:50 | Topics and Pub/Sub Contract Matrix

Say:
"Topic names are centralized, and topic ownership is explicitly defined."

Show on screen:
- Topic constants
- message definitions with publisher/subscriber and required payload fields

Code location:
- `src/retrieval_system/topics.py`
- `src/retrieval_system/message_definitions.py`

## 2:50 - 3:20 | Event Schema Validation

Say:
"All events must include type, topic, event_id, payload, and timestamp.  
This keeps messages consistent and testable."

Show on screen:
- `Event.from_dict`
- `EventValidationError`

Code location:
- `src/retrieval_system/contracts.py`

## 3:20 - 3:55 | Data Ownership and Storage Design

Say:
"DocumentDB service is the only writer for annotation documents.  
VectorIndex service is the only writer for vector records.  
This prevents direct bypass from CLI/API and keeps module boundaries clean."

Show on screen:
- `DocumentStore`
- `VectorIndexStore`

Code location:
- `src/retrieval_system/stores.py`

## 3:55 - 4:35 | Broker Layer: Memory vs Redis

Say:
"I implemented two bus backends.  
InMemoryEventBus is for deterministic testing and fault injection.  
RedisEventBus is for real pub-sub runtime."

Show on screen:
- `InMemoryEventBus` methods (`publish`, `tick`, drop/pause controls)
- `RedisEventBus` (`subscribe`, `publish`, `close`)

Code location:
- `src/retrieval_system/bus.py`

## 4:35 - 5:20 | Testing and Reliability Guarantees

Say:
"Tests validate idempotency, robustness, eventual consistency, and query correctness.  
Failure injection includes duplicates, delayed messages, dropped messages, and subscriber downtime."

Show on screen:
- End-to-end and idempotency tests
- failure-mode tests

Code location:
- `tests/test_pipeline.py`
- `tests/test_failures.py`
- `tests/test_contracts.py`
- `tests/test_message_definitions.py`

## 5:20 - 5:50 | Runtime Proof in Terminal

Say:
"Now I show runtime evidence: Redis up, tests passing, and end-to-end demos."

Run:
```bash
brew services start redis
redis-cli ping
python3 -m pytest -q
python3 scripts/run_demo.py --broker redis
```

Show on screen:
- Terminal output
- Optional screenshot artifacts

Code location:
- `scripts/check_submission.sh`
- `artifacts/screenshots/01_redis_status.png`
- `artifacts/screenshots/02_pytest.png`
- `artifacts/screenshots/04_demo_redis.png`

## 5:50 - 6:00 | Closing

Say:
"This project satisfies the assignment by delivering modular event-driven architecture, explicit contracts, Redis integration, and defensive tests."

Show on screen:
- `docs/DELIVERABLES.md`
