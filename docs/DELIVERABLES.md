# EC530 Project 2 Deliverables Mapping

This file maps the assignment requirements to concrete implementation artifacts.

## 1. Define services and data ownership

- `UploadService`: receives upload command and publishes `image.submitted`.
- `InferenceService`: simulates AI output and publishes `inference.completed`.
- `DocumentDBService`: **only owner** of document-DB state (`DocumentStore`).
- `EmbeddingService`: generates deterministic embeddings from stored documents.
- `VectorIndexService`: **only owner** of vector-index state (`VectorIndexStore`).
- `QueryService`: processes `query.submitted`, publishes `query.completed`.
- `CLIService`: user-facing simulation, never writes stores directly.

Code:
- `src/retrieval_system/services.py`
- `src/retrieval_system/stores.py`

## 2. Topics + publish/subscribe matrix

| Topic | Publisher | Subscribers |
|---|---|---|
| `image.submitted` | `UploadService/CLIService` | `InferenceService` |
| `inference.completed` | `InferenceService` | `DocumentDBService` |
| `annotation.stored` | `DocumentDBService` | `EmbeddingService` |
| `embedding.created` | `EmbeddingService` | `VectorIndexService` |
| `annotation.corrected` | `CLIService/Reviewer` | `DocumentDBService` |
| `query.submitted` | `CLIService` | `QueryService` |
| `query.completed` | `QueryService` | `CLIService` |

Code:
- `src/retrieval_system/topics.py`
- `src/retrieval_system/message_definitions.py`

## 3. Message structure and event contract

Required top-level fields:
- `type`
- `topic`
- `event_id`
- `payload`
- `timestamp`

Required payload fields are topic-specific and validated via:
- `src/retrieval_system/message_definitions.py`

Shared event schema validation:
- `src/retrieval_system/contracts.py`

## 4. Use REDIS pub-sub

Implemented adapters:
- `InMemoryEventBus` for deterministic tests
- `RedisEventBus` for real pub-sub with Redis channels

Code:
- `src/retrieval_system/bus.py`

Run with Redis:
```bash
python3 -m pip install redis
python3 scripts/run_demo.py --broker redis
```

## 5. Unit tests and defensive testing

Covered guarantees:
- **Idempotency**: duplicate events do not duplicate state.
- **Robustness**: malformed messages are rejected/logged.
- **Eventual consistency**: delayed delivery converges after ticks.
- **Accurate queries**: query results reflect processed index state.
- **Failure injection**: duplicates, dropped messages, delayed delivery, subscriber downtime.
- **Deterministic + replay mode**: event generator seed and JSONL replay.
- **Mockable publish()**: generator can be tested without live broker.

Code:
- `tests/test_contracts.py`
- `tests/test_pipeline.py`
- `tests/test_failures.py`
- `tests/test_event_generator.py`
- `tests/test_message_definitions.py`

## 6. What is intentionally not implemented

- No model training.
- No ANN algorithm implementation.
- Embeddings are deterministic simulation vectors for system integration focus.
