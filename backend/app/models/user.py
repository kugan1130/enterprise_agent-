"""SQLAlchemy models for User Authentication and Document Management."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """User account model for Auth & RBAC."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user") # 'user' or 'admin'
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentRecord(Base):
    """Metadata record for uploaded enterprise documents."""

    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(100), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    safe_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(String(50), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
