"""Document management API endpoints (Upload, List, Delete, Deduplication)."""

import hashlib
import logging
from pathlib import Path
from typing import Annotated, List, Dict, Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.user import DocumentRecord, User
from backend.app.rag.ingest import ingest_document_rag

logger = logging.getLogger("enterprise_ai.documents")
router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    document_id: str
    filename: str
    file_size: int
    uploaded_by: str
    user_id: Optional[int]
    status: str
    rag_status: str
    chunk_count: Optional[int]
    message: Optional[str] = None


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Uploads a PDF/document, checks SHA256 deduplication, extracts text, and indexes in ChromaDB."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    content_hash = hashlib.sha256(file_bytes).hexdigest()
    document_id = f"doc_{content_hash[:40]}"

    # Check for existing document by content hash
    existing = db.query(DocumentRecord).filter(
        (DocumentRecord.content_hash == content_hash) | (DocumentRecord.document_id == document_id)
    ).first()

    if existing and existing.status == "indexed" and (existing.chunk_count or 0) > 0:
        logger.info("SHA256 Deduplication: Document %s (%s) already indexed.", file.filename, content_hash[:8])
        return DocumentResponse(
            id=existing.id,
            document_id=existing.document_id,
            filename=existing.filename,
            file_size=existing.file_size,
            uploaded_by=existing.uploaded_by,
            user_id=existing.user_id,
            status=existing.status,
            rag_status=existing.rag_status,
            chunk_count=existing.chunk_count,
            message="Document already indexed (duplicate content detected).",
        )

    # Save to disk
    user_dir = settings.DATA_DIR / "documents" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / file.filename
    file_path.write_bytes(file_bytes)

    try:
        res = ingest_document_rag(
            file_path=file_path,
            db=db,
            filename=file.filename,
            safe_filename=file.filename,
            uploaded_by=str(current_user.username),
            source_path=str(file_path),
            user_id=current_user.id,
        )

        doc_rec = db.query(DocumentRecord).filter(DocumentRecord.document_id == document_id).first()
        if not doc_rec:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save document record.")

        rec: Any = doc_rec
        return DocumentResponse(
            id=rec.id,
            document_id=rec.document_id,
            filename=rec.filename,
            file_size=rec.file_size,
            uploaded_by=rec.uploaded_by,
            user_id=rec.user_id,
            status=rec.status,
            rag_status=rec.rag_status,
            chunk_count=rec.chunk_count,
            message="Document processed and indexed successfully.",
        )

    except Exception as err:
        logger.error("Document upload/indexing error for %s: %s", file.filename, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(err)}",
        )


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all uploaded document records belonging to the authenticated user (or all for admin)."""
    if current_user.role == "admin":
        docs = db.query(DocumentRecord).all()
    else:
        docs = db.query(DocumentRecord).filter(
            (DocumentRecord.user_id == current_user.id) | (DocumentRecord.uploaded_by == current_user.username)
        ).all()

    res_list = []
    for d in docs:
        item: Any = d
        res_list.append(
            DocumentResponse(
                id=item.id,
                document_id=item.document_id,
                filename=item.filename,
                file_size=item.file_size,
                uploaded_by=item.uploaded_by,
                user_id=item.user_id,
                status=item.status,
                rag_status=item.rag_status,
                chunk_count=item.chunk_count,
            )
        )
    return res_list


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a document record and purges its vector embeddings from ChromaDB."""
    query = db.query(DocumentRecord).filter(
        (DocumentRecord.document_id == document_id) | (DocumentRecord.id == int(document_id) if document_id.isdigit() else False)
    )
    if current_user.role != "admin":
        query = query.filter(
            (DocumentRecord.user_id == current_user.id) | (DocumentRecord.uploaded_by == current_user.username)
        )

    doc = query.first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or unauthorized.")

    # Remove from ChromaDB
    try:
        from backend.app.core.chroma import get_chroma_client
        client = get_chroma_client()
        collection = client.get_or_create_collection(name="enterprise_documents")
        existing_chunks = collection.get(where={"document_id": doc.document_id})["ids"]
        if existing_chunks:
            collection.delete(ids=existing_chunks)
    except Exception as err:
        logger.warning("Notice while purging ChromaDB chunks for document %s: %s", doc.document_id, err)

    # Delete record
    db.delete(doc)
    db.commit()

    return {"status": "success", "message": f"Document {document_id} deleted successfully."}
