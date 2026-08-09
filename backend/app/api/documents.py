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
        if existing.status == "indexed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document already uploaded and indexed."
            )
        elif existing.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document is already being processed."
            )
        # If failed, we allow reprocessing

    # Ensure storage directory exists
    storage_dir = settings.DATA_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)
    save_path = storage_dir / f"upload_{uuid.uuid4().hex}.pdf"

    with open(save_path, "wb") as f:
        f.write(content)

    source_path = f"uploads/{Path(file.filename).name}"

    if not existing:
        from datetime import datetime
        existing = DocumentRecord(
            document_id=document_id,
            filename=file.filename,
            original_filename=file.filename,
            safe_filename=save_path.name,
            file_type="PDF",
            file_size=len(content),
            uploaded_by=current_user.username,
            storage_path=str(save_path),
            source_path=source_path,
            content_hash=file_hash,
            chunk_count=0,
            status="processing",
            rag_status="processing",
            sql_status="not_applicable",
            error_message=None,
            user_id=current_user.id
        )
        db.add(existing)
    else:
        existing.status = "processing"
        existing.rag_status = "processing"
        existing.error_message = None
        existing.storage_path = str(save_path)
    
    db.commit()

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
    records = db.query(DocumentRecord).all()
    return [
        {
            "id": r.document_id,
            "document_id": r.document_id, # for frontend UI compatibility
            "filename": r.filename,
            "file_type": r.file_type or "PDF",
            "status": r.status,
            "rag_status": r.rag_status,
            "sql_status": r.sql_status,
            "chunk_count": r.chunk_count or 0,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "file_size": r.file_size,
            "uploaded_by": r.uploaded_by,
            "upload_timestamp": r.upload_timestamp.isoformat() if r.upload_timestamp else None,
        }
        for r in records
    ]

@router.get("/{document_id}")
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns a specific document record."""
    record = db.query(DocumentRecord).filter(DocumentRecord.document_id == document_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    return {
        "id": record.document_id,
        "filename": record.filename,
        "file_type": record.file_type or "PDF",
        "status": record.status,
        "rag_status": record.rag_status,
        "sql_status": record.sql_status,
        "chunk_count": record.chunk_count or 0,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a document and its associated data."""
    record = db.query(DocumentRecord).filter(DocumentRecord.document_id == document_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # 1. Delete ChromaDB vectors
    from backend.app.core.chroma import get_chroma_service
    try:
        get_chroma_service().delete_document("enterprise_documents", document_id)
    except Exception as e:
        import logging
        logging.getLogger("enterprise_ai").error(f"Failed to delete vectors for {document_id}: {e}")

    # 2. Delete Physical File
    if record.storage_path:
        try:
            p = Path(record.storage_path)
            if p.exists():
                p.unlink()
        except Exception as e:
            import logging
            logging.getLogger("enterprise_ai").error(f"Failed to delete file for {document_id}: {e}")
            
    # 3. Optional: SQL Table Drop (if implemented for CSV/SQL)
    if record.sql_table_name:
        try:
            from sqlalchemy import text
            db.execute(text(f"DROP TABLE IF EXISTS {record.sql_table_name}"))
        except Exception as e:
            import logging
            logging.getLogger("enterprise_ai").error(f"Failed to drop SQL table for {document_id}: {e}")

    # 4. Delete Record
    db.delete(record)
    db.commit()
    
    return {"status": "success", "message": f"Document {document_id} deleted."}
