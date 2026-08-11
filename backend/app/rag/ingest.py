"""PDF document ingestion into persistent ChromaDB vector store with clean text extraction."""

import logging
import hashlib
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast, List, Dict, Any

import chromadb
from chromadb.api.types import Embedding, Metadata
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.rag.embeddings import embed_passages
from backend.app.models.user import DocumentRecord

COLLECTION_NAME = "enterprise_documents"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHROMA_PATH = PROJECT_ROOT / ".data" / "chroma"

logger = logging.getLogger("enterprise_ai.rag_ingest")


@dataclass
class IngestionResult:
    document_id: str
    chunk_count: int
    skipped: bool


def _prune_legacy_duplicates(collection, filename: str, kept_ids: set) -> None:
    """Removes pre-refactor chunks that used filename-based document IDs instead of content hashes."""
    try:
        matches = collection.get(where={"filename": filename}, include=["metadatas"])
        to_delete = [
            chunk_id
            for chunk_id, meta in zip(matches["ids"], matches["metadatas"])
            if chunk_id not in kept_ids and (
                str(meta.get("content_hash", "")).strip() == ""
                or str(meta.get("document_id", "")) == Path(filename).stem
            )
        ]
        if to_delete:
            collection.delete(ids=to_delete)
            logger.info("Pruned %d legacy duplicate chunks for %s", len(to_delete), filename)
    except Exception as err:
        logger.warning("Legacy chunk pruning notice for %s: %s", filename, err)


def _extract_pdf_text_clean(pdf_path: Path) -> List[str]:
    """Extracts page text from PDF using pypdf.PdfReader."""
    pages_text = []
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        for page_idx, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            if txt.strip():
                pages_text.append(txt)
    except Exception as err:
        logger.warning("pypdf extraction warning on %s: %s", pdf_path.name, err)
    return pages_text


def ingest_document_rag(
    file_path: Path,
    *,
    db: Any,
    filename: str,
    safe_filename: str,
    uploaded_by: str,
    source_path: str,
    user_id: Any = None,
    persist_path: Path = DEFAULT_CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
) -> IngestionResult:
    """The single ingestion path for filesystem and uploaded documents into RAG."""
    content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    document_id = f"doc_{content_hash[:40]}"
    
    # Check by content_hash or document_id
    existing = db.query(DocumentRecord).filter(
        (DocumentRecord.content_hash == content_hash) | (DocumentRecord.document_id == document_id)
    ).first()

    if existing and (existing.status == "indexed" or existing.rag_status == "indexed") and (existing.chunk_count or 0) > 0:
        logger.info("Document %s (%s) already indexed with %d chunks. Skipping.", filename, content_hash[:8], existing.chunk_count)
        return IngestionResult(document_id=existing.document_id, chunk_count=existing.chunk_count or 0, skipped=True)

    if not existing:
        existing = DocumentRecord(
            document_id=document_id,
            filename=filename,
            safe_filename=safe_filename,
            file_size=file_path.stat().st_size,
            uploaded_by=uploaded_by,
            user_id=int(user_id) if user_id is not None else None,
            upload_timestamp=datetime.utcnow(),
            source_path=source_path,
            content_hash=content_hash,
            chunk_count=0,
            status="processing"
        )
        db.add(existing)
        db.commit()
    else:
        if user_id is not None and not existing.user_id:
            existing.user_id = int(user_id)
            db.commit()

    try:
        from backend.app.core.chroma import get_chroma_service
        chroma_service = get_chroma_service(persist_path)
        client = chroma_service.get_raw_client()
        collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        
        documents = []
        ext = file_path.suffix.lower()
        from langchain_core.documents import Document

        if ext == ".pdf":
            try:
                from langchain_community.document_loaders import PyPDFLoader
                pdf_docs = PyPDFLoader(str(file_path)).load()
                if pdf_docs:
                    documents = pdf_docs
            except Exception:
                pass

            if not documents:
                extracted_pages = _extract_pdf_text_clean(file_path)
                for page_idx, page_text in enumerate(extracted_pages):
                    documents.append(
                        Document(
                            page_content=page_text,
                            metadata={"source": file_path.name, "page": page_idx},
                        )
                    )
        elif ext == ".csv":
            import csv
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                try:
                    headers = next(reader)
                    for i, row in enumerate(reader):
                        content = ", ".join(f"{h}: {v}" for h, v in zip(headers, row) if v.strip())
                        if content:
                            documents.append(
                                Document(
                                    page_content=content,
                                    metadata={"source": file_path.name, "row": i},
                                )
                            )
                except StopIteration:
                    pass
        elif ext == ".sql":
            content = file_path.read_text(encoding="utf-8")
            if content.strip():
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"source": file_path.name},
                    )
                )

        if not documents:
            raise ValueError(f"No extractable text found in {file_path.name}.")

        chunks = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        ).split_documents(documents)

        texts: List[str] = []
        ids: List[str] = []
        metadatas: List[Metadata] = []

        uid_val = int(user_id) if user_id is not None else 0

        for idx, chunk in enumerate(chunks):
            content = chunk.page_content.strip()
            if not content:
                continue
            chunk_id = f"{document_id}-c{idx}"
            ids.append(chunk_id)
            texts.append(content)
            metadatas.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "source": filename,
                    "source_path": source_path,
                    "content_hash": content_hash,
                    "uploaded_by": uploaded_by,
                    "user_id": uid_val,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "page": chunk.metadata.get("page", 0),
                    "source_type": ext.lstrip(".")
                }
            )

        if not texts:
            raise ValueError(f"No non-empty text chunks found in {file_path.name}.")

        # Replace all prior chunks
        existing_chunks = collection.get(where={"document_id": document_id})["ids"]
        if existing_chunks:
            collection.delete(where={"document_id": document_id})
        
        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=cast(List[Embedding], embed_passages(texts)),
        )
        
        # Verify ChromaDB insertion
        inserted = collection.get(where={"document_id": document_id})["ids"]
        if len(inserted) != len(texts):
            raise RuntimeError(f"ChromaDB insertion mismatch: expected {len(texts)} but inserted {len(inserted)} chunks.")

        _prune_legacy_duplicates(collection, filename, set(ids))
        
        # Update PostgreSQL (status=indexed)
        existing.status = "indexed"
        existing.rag_status = "indexed"
        existing.chunk_count = len(texts)
        db.commit()
        
        return IngestionResult(document_id=document_id, chunk_count=len(texts), skipped=False)
        
    except Exception as err:
        logger.error(f"Ingestion failed for {filename}: {err}")
        existing.status = "failed"
        existing.rag_status = "failed"
        existing.error_message = str(err)
        db.commit()
        raise err


def ingest_documents(documents_path: Path, *, db: Any = None, persist_path: Path = DEFAULT_CHROMA_PATH, collection_name: str = COLLECTION_NAME) -> int:
    """Ingest all supported company PDFs through the common PDF ingestion path."""
    if db is None:
        from backend.app.core.database import SessionLocal

        with SessionLocal() as session:
            return ingest_documents(
                documents_path,
                db=session,
                persist_path=persist_path,
                collection_name=collection_name,
            )

    total_chunks = 0
    for pdf_path in sorted(documents_path.glob("*.pdf")):
        result = ingest_document_rag(
            pdf_path,
            db=db,
            filename=pdf_path.name,
            safe_filename=pdf_path.name,
            uploaded_by="system",
            source_path=str(pdf_path),
            persist_path=persist_path,
            collection_name=collection_name,
        )
        total_chunks += result.chunk_count
    return total_chunks
