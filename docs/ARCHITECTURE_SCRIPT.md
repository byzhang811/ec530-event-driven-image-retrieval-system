# Short Architecture Video Script (2-3 minutes)

## 1. Problem and scope

"This project implements an event-driven image annotation and retrieval system.  
The goal is system integration and testability, not model training or ANN implementation."

## 2. Service boundaries and ownership

"I split the system into Upload, Inference, DocumentDB, Embedding, VectorIndex, Query, and CLI services.  
Data ownership is strict: only DocumentDB service writes annotation documents, and only VectorIndex service writes vector records.  
CLI never bypasses services to write stores directly."

## 3. Event flow

"Upload publishes `image.submitted`.  
Inference consumes that and publishes `inference.completed`.  
DocumentDB persists a JSON-like annotation record and publishes `annotation.stored`.  
Embedding consumes `annotation.stored`, creates deterministic embeddings, and publishes `embedding.created`.  
VectorIndex consumes `embedding.created` and updates search state.  
For retrieval, CLI publishes `query.submitted`, Query service returns `query.completed`."

## 4. Message contract and testability

"Every event uses one contract with `type`, `topic`, `event_id`, `payload`, and `timestamp`.  
Each topic also has required payload fields and publisher/subscriber definitions."

## 5. Verification

"Tests cover idempotency, malformed event robustness, delayed delivery convergence, dropped messages, subscriber downtime, deterministic generation, replay mode, and query correctness.  
The suite passes in-memory and the same architecture runs with Redis pub-sub."

## 6. Closing

"This design emphasizes modularity, defensive testing, and evolvable data models, which aligns with the assignment grading criteria."
