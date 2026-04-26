# Presentation Script (English, 5-6 Minutes)

> Estimated duration: about 5 to 6 minutes  
> You can read this script directly.

## 0) Opening (15-20s)

Hello everyone.  
Today I will present my EC530 Project 2: an **Event-Driven Image Annotation and Retrieval System**.  
The focus of this project is not model training.  
The focus is software engineering: architecture, service boundaries, messaging design, and testability.

## 1) Problem and Scope (35-45s)

This system supports two retrieval use cases:
1. Given an image, return top-k similar images or objects.
2. Given a text topic, return relevant image or object results.

To follow the assignment scope, I did **not** train models and did **not** implement ANN algorithms.  
Instead, I simulated inference and embedding generation so I could focus on building a clean event-driven pipeline.

## 2) High-Level Architecture (55-70s)

The system is split into seven services:
1. `UploadService`
2. `InferenceService`
3. `DocumentDBService`
4. `EmbeddingService`
5. `VectorIndexService`
6. `QueryService`
7. `CLIService`

The main event topics are:
- `image.submitted`
- `inference.completed`
- `annotation.stored`
- `embedding.created`
- `annotation.corrected`
- `query.submitted`
- `query.completed`

The core asynchronous pipeline is:
`image.submitted -> inference.completed -> annotation.stored -> embedding.created`

For retrieval:
`query.submitted -> query.completed`

One key design rule is **single ownership of each datastore**:
- Document records are written only by `DocumentDBService`.
- Vector index records are written only by `VectorIndexService`.
- CLI and API do not bypass services to write data directly.

## 3) Message Contracts and Reliability (40-55s)

Every event uses the same contract with required top-level fields:
- `type`
- `topic`
- `event_id`
- `payload`
- `timestamp`

In addition, each topic has topic-specific required payload fields.  
This gives us strong validation, easier debugging, and repeatable tests.

I also built defensive behavior for reliability goals:
- Idempotency for duplicate events
- Robust handling of malformed messages
- Eventual consistency under delayed delivery
- Query results that reflect current processed state

## 4) Code Walkthrough by File (about 2 minutes)

Now I will quickly map the key files to responsibilities.

In `src/retrieval_system/topics.py`, I define all canonical topic names used across services.

In `src/retrieval_system/contracts.py`, I define the event object, timestamp parsing and formatting, event ID helpers, and schema validation.

In `src/retrieval_system/message_definitions.py`, I define the publisher/subscriber matrix and required payload fields for each topic, plus payload-level validation.

In `src/retrieval_system/bus.py`, I implement two bus backends:
- `InMemoryEventBus` for deterministic local tests and fault injection
- `RedisEventBus` for real pub-sub integration with Redis channels

In `src/retrieval_system/stores.py`, I define:
- `DocumentStore` for JSON-like annotation documents with nested and variable fields
- `VectorIndexStore` for vector records and similarity query

In `src/retrieval_system/vector_math.py`, I provide deterministic pseudo-embedding generation and cosine similarity, so the system is testable without model training.

In `src/retrieval_system/services.py`, I implement all service behaviors and topic handlers:
- ingestion
- simulated inference
- document persistence
- embedding creation
- vector indexing
- query processing
- query result collection in CLI

In `src/retrieval_system/event_generator.py`, I implement deterministic event generation with seed control and replay from JSONL datasets.

In `src/retrieval_system/system.py`, I wire all services together into one runnable system entrypoint.

For tests:
- `tests/test_contracts.py` validates event schema behavior.
- `tests/test_message_definitions.py` validates topic payload requirements.
- `tests/test_event_generator.py` checks deterministic generation and replay mode.
- `tests/test_pipeline.py` checks end-to-end flow and idempotency.
- `tests/test_failures.py` checks delayed delivery, dropped messages, subscriber downtime, malformed events, and query state consistency.

For reproducible validation artifacts:
- `scripts/check_submission.sh` runs Redis checks, tests, and both demos.
- `scripts/generate_terminal_screenshots.py` turns logs into screenshot-ready PNG evidence.

## 5) Runtime Evidence and Screenshots (55-70s)

Now I will show runtime evidence.

First, Redis startup and health check:
- `brew services start redis`
- `redis-cli ping`
- `brew services list | rg '^redis\\s'`

Screenshot:
![Redis Status](../artifacts/screenshots/01_redis_status.png)

Second, full unit test result:
- `python3 -m pytest -q`
- Current result is `23 passed`.

Screenshot:
![Pytest Result](../artifacts/screenshots/02_pytest.png)

Third, end-to-end demo on in-memory bus:
- `python3 scripts/run_demo.py --broker memory`

Screenshot:
![Demo Memory](../artifacts/screenshots/03_demo_memory.png)

Fourth, end-to-end demo on Redis bus:
- `python3 scripts/run_demo.py --broker redis`

Screenshot:
![Demo Redis](../artifacts/screenshots/04_demo_redis.png)

These outputs confirm that the architecture works both in deterministic local mode and in real Redis pub-sub mode.

## 6) Closing (20-30s)

To conclude, this project satisfies the assignment requirements by delivering:
- a modular event-driven architecture,
- explicit messaging contracts,
- strict data ownership boundaries,
- Redis integration,
- and comprehensive defensive testing.

The repository is complete, and the architecture video link placeholder is left blank in README so I can add my recording link afterward.  
Thank you.
