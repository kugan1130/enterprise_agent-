"""PDF Upload and Document Ingestion API endpoints."""

import uuid
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db, require_admin_user
from backend.app.core.config import settings
from backend.app.models.user import DocumentRecord, User
from backend.app.rag.ingest import ingest_pdf

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads and automatically ingests a PDF document into ChromaDB for RAG search.
    Enforces file type, size limits, safe UUID naming, and automatic vector indexing.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF documents (.pdf) are allowed.",
        )

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    # 1. Pre-ingestion duplicate check
    import hashlib
    file_hash = hashlib.sha256(content).hexdigest()
    document_id = f"doc_{file_hash[:40]}"
    
    existing = db.query(DocumentRecord).filter(DocumentRecord.document_id == document_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already uploaded/indexed."
        )

    # Ensure storage directory exists
    storage_dir = settings.DATA_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)
    save_path = storage_dir / f"upload_{uuid.uuid4().hex}.pdf"

    with open(save_path, "wb") as f:
        f.write(content)

    try:
        result = ingest_pdf(
            save_path,
            db=db,
            filename=file.filename,
            safe_filename=save_path.name,
            uploaded_by=current_user.username,
            source_path=f"uploads/{Path(file.filename).name}",
        )
    except Exception as err:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process and index PDF: {err}",
        )

    return {
        "document_id": result.document_id,
        "filename": file.filename,
        "chunks_ingested": result.chunk_count,
        "status": "already_ingested" if result.skipped else "ingested",
        "message": f"{file.filename} is ready. You can now ask questions about it.",
    }


@router.get("")
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns list of uploaded documents."""
    records = db.query(DocumentRecord).filter(DocumentRecord.status == "indexed").all()
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
