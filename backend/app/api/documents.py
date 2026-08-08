"""PDF Upload and Document Management API endpoints."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db, require_admin_user
from backend.app.core.config import settings
from backend.app.models.user import DocumentRecord, User
from backend.app.rag.ingest import ingest_single_pdf

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads and automatically ingests a PDF document into ChromaDB for RAG search.
    Enforces file type, file size limits, safe UUID naming, and authentication.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents are allowed.",
        )

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # Generate safe unique document identifier
    doc_uuid = uuid.uuid4().hex[:12]
    document_id = f"doc_{doc_uuid}"
    safe_filename = f"{document_id}.pdf"

    # Ensure storage directory exists
    storage_dir = settings.DATA_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)
    save_path = storage_dir / safe_filename

    with open(save_path, "wb") as f:
        f.write(content)

    timestamp_str = datetime.utcnow().isoformat()

    metadata = {
        "document_id": document_id,
        "filename": file.filename,
        "upload_timestamp": timestamp_str,
        "uploaded_by": current_user.username,
    }

    try:
        chunks_ingested = ingest_single_pdf(save_path, metadata)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document into ChromaDB: {err}",
        )

    # Store record in PostgreSQL
    doc_record = DocumentRecord(
        document_id=document_id,
        filename=file.filename,
        safe_filename=safe_filename,
        file_size=len(content),
        uploaded_by=current_user.username,
        upload_timestamp=datetime.utcnow(),
    )
    db.add(doc_record)
    db.commit()

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunks_ingested": chunks_ingested,
        "status": "ingested",
    }


@router.get("")
def list_documents(
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint listing all uploaded document records."""
    records = db.query(DocumentRecord).all()
    return [
        {
            "document_id": r.document_id,
            "filename": r.filename,
            "file_size": r.file_size,
            "uploaded_by": r.uploaded_by,
            "upload_timestamp": r.upload_timestamp.isoformat() if r.upload_timestamp else None,
        }
        for r in records
    ]
