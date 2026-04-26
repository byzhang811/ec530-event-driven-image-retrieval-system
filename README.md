# EC530 Project 2: Event-Driven Image Annotation and Retrieval System

## Submission Links

- Repository: *(this GitHub repo)*
- Architecture video: 
- Presentation script (EN, 5-6 min): `docs/PRESENTATION_SCRIPT_EN.md`

This repository implements the assignment scaffold from **Boston University EC530 Project 2**:

- Event-driven architecture with pub-sub topics
- Document database model for variable/nested annotations
- Vector index integration for similarity retrieval
- Deterministic event generator and replay flow
- Unit tests focused on **idempotency, robustness, eventual consistency, and query correctness**

## Assignment Focus (From Slides)

- You are graded on architecture, testability, and design justification.
- Do not train models.
- Do not implement ANN algorithms.
- Use provided embeddings/simple model and focus on system integration.
- Suggested broker is Redis pub-sub (any bus is acceptable).

Important date called out in the slides:
- **Tuesday, April 14, 2026**: project structure + message definitions + Redis topics/messages + testing.

## Architecture

Services:
- `UploadService`: receives uploads and publishes `image.submitted`.
- `InferenceService`: consumes `image.submitted`, simulates detections, publishes `inference.completed`.
- `DocumentDBService`: owns annotation documents, consumes `inference.completed`, publishes `annotation.stored`.
- `EmbeddingService`: consumes `annotation.stored`, builds deterministic embeddings, publishes `embedding.created`.
- `VectorIndexService`: owns vector records, consumes `embedding.created`, serves similarity search.
- `QueryService`: consumes `query.submitted`, runs retrieval through `VectorIndexService`, publishes `query.completed`.
- `CLIService`: simulates user uploads and queries, consumes `query.completed`.

### Data ownership rule

Only one service owns each data store:
- Document DB state is owned only by `DocumentDBService`.
- Vector index state is owned only by `VectorIndexService`.

CLI and API paths do not write directly to stores.

## Topics

- `image.submitted`
- `inference.completed`
- `annotation.stored`
- `embedding.created`
- `annotation.corrected`
- `query.submitted`
- `query.completed`

## Event Contract

All messages follow the shared schema:

```json
{
  "type": "publish",
  "topic": "image.submitted",
  "event_id": "evt_1042",
  "payload": {
    "image_id": "img_1042",
    "path": "images/street_1042.jpg",
    "source": "camera_A",
    "timestamp": "2026-04-07T14:33:00Z"
  },
  "timestamp": "2026-04-07T14:33:00Z"
}
```

Topic-specific payload requirements (publisher/subscriber ownership) are defined in:
- `src/retrieval_system/message_definitions.py`
- `docs/DELIVERABLES.md`

## Event Bus Options

- `InMemoryEventBus`: deterministic local testing; supports delayed delivery, dropped topics, and pause/resume subscriptions for failure injection.
- `RedisEventBus`: adapter for Redis pub-sub channels.

## Deterministic Event Generator

`EventGenerator` supports:
- deterministic mode with seed
- replay mode from JSONL event dataset (`data/sample_events.jsonl`)

## Quick Start

```bash
python3 -m pytest -q
```

Run an end-to-end demo in memory:

```bash
python3 scripts/run_demo.py --broker memory
```

Run an end-to-end demo on Redis pub-sub:

```bash
brew install redis
brew services start redis
python3 -m pip install redis
python3 scripts/run_demo.py --broker redis
```

Run the full submission check and generate screenshot evidence:

```bash
./scripts/check_submission.sh
python3 scripts/generate_terminal_screenshots.py
```

## Repository Layout

```text
src/retrieval_system/
  contracts.py
  message_definitions.py
  topics.py
  bus.py
  stores.py
  vector_math.py
  services.py
  event_generator.py
  system.py
tests/
data/
docs/
scripts/
```
