"""Local E5 embedding helpers with fallback protection."""

import logging
from functools import lru_cache

logger = logging.getLogger("enterprise_ai.embeddings")
MODEL_NAME = "intfloat/multilingual-e5-large"
_embedding_model = None


@lru_cache
def get_embedding_model():
    """Load the embedding model once per process."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(MODEL_NAME)
        return _embedding_model
    except Exception as err:
        logger.warning("Unable to load SentenceTransformer '%s' (%s).", MODEL_NAME, err)
        return None


def embed_passages(passages: list[str]) -> list[list[float]]:
    """Embed document chunks using the E5 passage convention."""
    model = get_embedding_model()
    if model is not None:
        return model.encode(
            [f"passage: {passage}" for passage in passages],
            normalize_embeddings=True,
        ).tolist()

    raise RuntimeError(f"Embedding model '{MODEL_NAME}' is unavailable; refusing to index unusable vectors.")


def embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the E5 query convention."""
    model = get_embedding_model()
    if model is not None:
        return model.encode(
            f"query: {query}",
            normalize_embeddings=True,
        ).tolist()

    raise RuntimeError(f"Embedding model '{MODEL_NAME}' is unavailable; retrieval is unavailable.")
