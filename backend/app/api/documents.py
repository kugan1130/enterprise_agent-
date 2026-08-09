"""PDF Upload and Document Ingestion API endpoints."""

import uuid
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.auth import get_current_user, get_db, require_admin_user
from backend.app.core.config import settings
from backend.app.models.user import DocumentRecord, User
from backend.app.rag.ingest import ingest_document_rag
from backend.app.services.sql_ingestion import ingest_csv_to_sql, ingest_sql_file_to_sql

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads and automatically ingests a document into ChromaDB for RAG search.
    For structured data (.csv, .sql), also parallel-ingests into PostgreSQL.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")
        
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".csv", ".sql"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only .pdf, .csv, and .sql are allowed.",
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
    save_path = storage_dir / f"upload_{uuid.uuid4().hex}{ext}"

    with open(save_path, "wb") as f:
        f.write(content)

    source_path = f"uploads/{Path(file.filename).name}"
    
    file_type = "PDF" if ext == ".pdf" else "CSV" if ext == ".csv" else "SQL"
    is_structured = ext in [".csv", ".sql"]

    if not existing:
        from datetime import datetime
        existing = DocumentRecord(
            document_id=document_id,
            filename=file.filename,
            original_filename=file.filename,
            safe_filename=save_path.name,
            file_type=file_type,
            file_size=len(content),
            uploaded_by=current_user.username,
            storage_path=str(save_path),
            source_path=source_path,
            content_hash=file_hash,
            chunk_count=0,
            status="processing",
            rag_status="processing",
            sql_status="processing" if is_structured else "not_applicable",
            error_message=None,
            user_id=current_user.id
        )
        db.add(existing)
    else:
        existing.status = "processing"
        existing.rag_status = "processing"
        if is_structured:
            existing.sql_status = "processing"
        existing.error_message = None
        existing.storage_path = str(save_path)
    
    db.commit()

    rag_error = None
    sql_error = None
    chunk_count = 0
    skipped_rag = False

    # 1. RAG Pipeline
    try:
        result = ingest_document_rag(
            save_path,
            db=db,
            filename=file.filename,
            safe_filename=save_path.name,
            uploaded_by=current_user.username,
            source_path=f"uploads/{Path(file.filename).name}",
        )
        chunk_count = result.chunk_count
        skipped_rag = result.skipped
    except Exception as err:
        rag_error = str(err)
        
    # 2. SQL Pipeline (if structured)
    if is_structured:
        try:
            if ext == ".csv":
                table_name = ingest_csv_to_sql(save_path, file.filename)
                existing.sql_table_name = table_name
            elif ext == ".sql":
                table_name = ingest_sql_file_to_sql(save_path, file.filename)
                existing.sql_table_name = table_name
            
            existing.sql_status = "indexed"
        except Exception as err:
            sql_error = str(err)
            existing.sql_status = "failed"
            
    # Finalize status based on dual pipelines
    if rag_error and (sql_error or not is_structured):
        # Both failed, or RAG failed and no SQL was attempted
        existing.status = "failed"
        existing.error_message = f"RAG Error: {rag_error}" + (f" | SQL Error: {sql_error}" if sql_error else "")
        db.commit()
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed completely: {existing.error_message}",
        )
    else:
        # At least one pipeline succeeded
        existing.status = "indexed"
        existing.error_message = f"Partial failure: RAG({rag_error}) SQL({sql_error})" if (rag_error or sql_error) else None
        db.commit()

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunks_ingested": chunk_count,
        "status": "already_ingested" if skipped_rag else "ingested",
        "message": f"{file.filename} is ready. RAG: {'Failed' if rag_error else 'OK'}, SQL: {'Failed' if sql_error else 'OK' if is_structured else 'N/A'}",
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
