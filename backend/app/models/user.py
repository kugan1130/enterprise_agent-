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
    document_id = Column(String(50), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    safe_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(String(50), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
