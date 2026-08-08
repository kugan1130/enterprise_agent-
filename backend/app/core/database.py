from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.core.config import settings

# Shared SQLAlchemy engine created from application settings
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# SessionLocal class factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to yield a database session and ensure closure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
