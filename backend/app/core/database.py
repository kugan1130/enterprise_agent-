"""SQLAlchemy database setup with dynamic PostgreSQL & SQLite fallback protection."""

import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.core.config import settings

logger = logging.getLogger("enterprise_ai.database")


def _get_engine():
    """Returns the SQLAlchemy engine based on configuration without silent SQLite fallbacks for PostgreSQL."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql"):
        try:
            # Use standard pool ping to ensure connection without an artificially low timeout
            engine = create_engine(db_url, pool_pre_ping=True)
            logger.info("Configured to connect to PostgreSQL database.")
            return engine
        except Exception as err:
            logger.error("PostgreSQL database configuration error: %s", err)
            raise RuntimeError(f"Failed to configure PostgreSQL engine: {err}")

    # Fallback only if explicitly configured for sqlite
    return create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )


engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield a database session and ensure closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
