"""PDF ingestion into a persistent Chroma collection."""

from pathlib import Path
from typing import cast

import chromadb
from chromadb.api.types import Embedding, Metadata
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
        try:
            from langchain_community.document_loaders import PyPDFLoader
            documents.extend(PyPDFLoader(str(pdf_path)).load())
        except Exception:
            from langchain_core.documents import Document
            with open(pdf_path, "rb") as f:
                raw_text = f.read().decode("latin1", errors="ignore")
            documents.append(Document(page_content=raw_text, metadata={"source": pdf_path.name, "page": 0}))

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1_000,
        chunk_overlap=150,
    ).split_documents(documents)
    texts = [chunk.page_content for chunk in chunks]
    ids = [f"{Path(chunk.metadata.get('source', 'doc')).stem}-{index}" for index, chunk in enumerate(chunks)]
    metadatas: list[Metadata] = [
        {
            "source": Path(chunk.metadata.get("source", "document.pdf")).name,
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


def ingest_single_pdf(
    pdf_path: Path,
    doc_metadata: dict,
    *,
    persist_path: Path = DEFAULT_CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
) -> int:
    """Load a single uploaded PDF file, chunk, embed, and upsert to ChromaDB."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
        documents = PyPDFLoader(str(pdf_path)).load()
    except Exception as err:
        print(f"PyPDFLoader notice ({err}), attempting raw fallback text extraction...")
        from langchain_core.documents import Document
        with open(pdf_path, "rb") as f:
            raw_text = f.read().decode("latin1", errors="ignore")
        documents = [Document(page_content=raw_text, metadata={"source": pdf_path.name, "page": 0})]

    if not documents:
        return 0

    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1_000,
        chunk_overlap=150,
    ).split_documents(documents)

    doc_id = doc_metadata.get("document_id", pdf_path.stem)
    texts = [chunk.page_content for chunk in chunks if chunk.page_content.strip()]
    if not texts:
        return 0

    ids = [f"{doc_id}-{idx}" for idx in range(len(texts))]

    metadatas: list[Metadata] = [
        {
            "document_id": doc_id,
            "filename": doc_metadata.get("filename", pdf_path.name),
            "source": doc_metadata.get("filename", pdf_path.name),
            "uploaded_by": doc_metadata.get("uploaded_by", "system"),
            "upload_timestamp": doc_metadata.get("upload_timestamp", ""),
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
    return len(texts)
