# EC530 Project 2
## Event-Driven Image Annotation and Retrieval System

## Student Information

- Name: Boyang Zhang
- Email: theostnc@bu.edu
- Course: EC530 Principles of Software Engineering
- University: Boston University

## Submission Links

- Repository: [GitHub Repository](https://github.com/byzhang811/ec530-event-driven-image-retrieval-system)
- Architecture Video: [Project Presentation Video](https://drive.google.com/file/d/1vKa4GqEkVEIxmyJ1I3JNB3u-6jbODmYo/view?usp=drive_link)

## Project Summary

This project implements an event-driven retrieval pipeline where image processing components communicate through pub-sub events instead of direct synchronous calls.

The design follows the assignment focus:
- modular architecture with clear service boundaries
- message-based integration with Redis pub-sub support
- document-style annotation storage for nested and variable fields
- vector indexing for similarity retrieval
- strong unit testing with deterministic replay and failure injection

## What This Project Includes

- Asynchronous event flow for image ingestion, annotation, embedding, and query
- Shared event schema and topic-specific payload validation
- In-memory event bus for deterministic testing
- Redis event bus adapter for real runtime integration
- Failure-mode testing for duplicates, delays, drops, and subscriber downtime
- Reproducible runtime evidence logs and screenshots

## Architecture Overview

Services:
- `UploadService`: publishes `image.submitted`
- `InferenceService`: consumes `image.submitted`, publishes `inference.completed`
- `DocumentDBService`: owns annotation documents, publishes `annotation.stored`
- `EmbeddingService`: consumes `annotation.stored`, publishes `embedding.created`
- `VectorIndexService`: owns vector index records, serves similarity retrieval
- `QueryService`: consumes `query.submitted`, publishes `query.completed`
- `CLIService`: user-facing simulation for uploads and queries

Core topics:
- `image.submitted`
- `inference.completed`
- `annotation.stored`
- `embedding.created`
- `annotation.corrected`
- `query.submitted`
- `query.completed`

## Data Ownership Rules

- Document DB state is owned only by `DocumentDBService`.
- Vector index state is owned only by `VectorIndexService`.
- CLI and API flows do not bypass services to write stores directly.

## Event Contract

All messages use this top-level contract:

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

Topic-level payload requirements are defined in:
- `src/retrieval_system/message_definitions.py`

## Setup

```bash
python3 -m pip install --user redis
brew install redis
brew services start redis
```

## How To Run

Run unit tests:

```bash
python3 -m pytest -q
```

Run end-to-end demo with in-memory bus:

```bash
python3 scripts/run_demo.py --broker memory
```

Run end-to-end demo with Redis bus:

```bash
python3 scripts/run_demo.py --broker redis
```

Run full submission verification:

```bash
./scripts/check_submission.sh
python3 scripts/generate_terminal_screenshots.py
```

## Runtime Evidence

Generated evidence files:
- Redis status log: `artifacts/logs/01_redis_status.log`
- Pytest log: `artifacts/logs/02_pytest.log`
- In-memory demo log: `artifacts/logs/03_demo_memory.log`
- Redis demo log: `artifacts/logs/04_demo_redis.log`

Generated screenshots:
- `artifacts/screenshots/01_redis_status.png`
- `artifacts/screenshots/02_pytest.png`
- `artifacts/screenshots/03_demo_memory.png`
- `artifacts/screenshots/04_demo_redis.png`

## Test Coverage Summary

The test suite validates:
- event schema and payload contracts
- deterministic generator and replay behavior
- end-to-end pipeline behavior
- idempotency under duplicate events
- malformed event robustness
- delayed delivery eventual consistency
- dropped message and subscriber downtime recovery
- query results consistent with processed state

## Repository Structure

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
artifacts/
```

## Notes

This implementation intentionally does not train models or implement ANN algorithms.  
It emphasizes system integration and software engineering quality, aligned with the assignment requirements.
