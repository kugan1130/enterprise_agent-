"""Local E5 embedding helpers."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-large"


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once per process."""
    return SentenceTransformer(MODEL_NAME)


def embed_passages(passages: list[str]) -> list[list[float]]:
    """Embed document chunks using the E5 passage convention."""
    return get_embedding_model().encode(
        [f"passage: {passage}" for passage in passages],
        normalize_embeddings=True,
    ).tolist()


def embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the E5 query convention."""
    return get_embedding_model().encode(
        f"query: {query}",
        normalize_embeddings=True,
    ).tolist()
