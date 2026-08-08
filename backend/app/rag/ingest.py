"""PDF ingestion into a persistent Chroma collection."""

from pathlib import Path
from typing import cast

import chromadb
from chromadb.api.types import Embedding, Metadata
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.rag.embeddings import embed_passages


COLLECTION_NAME = "enterprise_documents"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHROMA_PATH = PROJECT_ROOT / ".data" / "chroma"


def ingest_documents(
    documents_path: Path,
    *,
    persist_path: Path = DEFAULT_CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
) -> int:
    """Load PDFs, chunk them, and upsert their E5 vectors into Chroma."""
    pdf_paths = sorted(documents_path.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF documents found in {documents_path}")

    documents = []
    for pdf_path in pdf_paths:
        documents.extend(PyPDFLoader(str(pdf_path)).load())

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1_000,
        chunk_overlap=150,
    ).split_documents(documents)
    texts = [chunk.page_content for chunk in chunks]
    ids = [f"{Path(chunk.metadata['source']).stem}-{index}" for index, chunk in enumerate(chunks)]
    metadatas: list[Metadata] = [
        {
            "source": Path(chunk.metadata["source"]).name,
            "chunk_id": chunk_id,
            "page": chunk.metadata.get("page", 0),
        }
        for chunk, chunk_id in zip(chunks, ids, strict=True)
    ]

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=cast(list[Embedding], embed_passages(texts)),
    )
    return len(chunks)
