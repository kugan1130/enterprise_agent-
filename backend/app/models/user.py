"""SQLAlchemy ORM models for Users and Uploaded Document Records."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # 'user' or 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    document_id = Column(String(50), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    safe_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=True)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(String(50), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    storage_path = Column(String(500), nullable=True)
    source_path = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    chunk_count = Column(Integer, nullable=True)
    status = Column(String(20), default="processing", nullable=False)
    rag_status = Column(String(20), default="not_applicable", nullable=False)
    sql_status = Column(String(20), default="not_applicable", nullable=False)
    sql_table_name = Column(String(255), nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
