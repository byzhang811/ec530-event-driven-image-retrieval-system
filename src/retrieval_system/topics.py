"""Topic names for the pub-sub architecture."""

IMAGE_SUBMITTED = "image.submitted"
INFERENCE_COMPLETED = "inference.completed"
ANNOTATION_STORED = "annotation.stored"
EMBEDDING_CREATED = "embedding.created"
ANNOTATION_CORRECTED = "annotation.corrected"
QUERY_SUBMITTED = "query.submitted"
QUERY_COMPLETED = "query.completed"

ALL_TOPICS = {
    IMAGE_SUBMITTED,
    INFERENCE_COMPLETED,
    ANNOTATION_STORED,
    EMBEDDING_CREATED,
    ANNOTATION_CORRECTED,
    QUERY_SUBMITTED,
    QUERY_COMPLETED,
}
