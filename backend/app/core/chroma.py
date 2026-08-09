"""Centralized ChromaDB client configuration and singleton."""
import os
import logging
from pathlib import Path
import chromadb
from chromadb import PersistentClient

logger = logging.getLogger("enterprise_ai.chroma")

COLLECTION_NAME = "enterprise_documents"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHROMA_PATH = PROJECT_ROOT / ".data" / "chroma"

class ChromaService:
    def __init__(self, persist_path: Path = DEFAULT_CHROMA_PATH):
        self.persist_path = persist_path
        self._client = None

    def _get_client(self) -> PersistentClient:
        if self._client is None:
            logger.info(f"Initializing singleton ChromaDB client at {self.persist_path}")
            self._client = chromadb.PersistentClient(path=str(self.persist_path))
        return self._client

    def get_raw_client(self) -> PersistentClient:
        """Returns the raw PersistentClient for backward compatibility."""
        return self._get_client()

    def add_documents(self, collection_name: str, documents: list, metadatas: list, ids: list, embeddings: list = None):
        client = self._get_client()
        col = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        col.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def similarity_search(self, collection_name: str, query_embeddings: list, n_results: int = 5, where: dict = None):
        client = self._get_client()
        col = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        return col.query(query_embeddings=query_embeddings, n_results=n_results, where=where)

    def delete_document(self, collection_name: str, document_id: str):
        client = self._get_client()
        col = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        existing = col.get(where={"document_id": document_id})
        if existing and existing.get("ids"):
            col.delete(where={"document_id": document_id})

    def count(self, collection_name: str) -> int:
        client = self._get_client()
        col = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        return col.count()

    def health_check(self) -> str:
        """Verifies ChromaDB accessibility."""
        try:
            if self.persist_path.exists() or os.access(self.persist_path.parent, os.W_OK):
                # Optionally test client creation
                self._get_client()
                return "healthy"
        except Exception:
            pass
        return "unhealthy"

_chroma_service_instance = None

def get_chroma_service(persist_path: Path = DEFAULT_CHROMA_PATH) -> ChromaService:
    global _chroma_service_instance
    if _chroma_service_instance is None:
        _chroma_service_instance = ChromaService(persist_path)
    return _chroma_service_instance

def get_chroma_client(persist_path: Path = DEFAULT_CHROMA_PATH) -> PersistentClient:
    """Returns a singleton ChromaDB PersistentClient."""
    return get_chroma_service(persist_path).get_raw_client()
