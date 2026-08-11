"""Automatic startup seeder for PostgreSQL sales database and company PDF documents."""

import logging
from pathlib import Path
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, engine
from backend.app.rag.ingest import ingest_documents

logger = logging.getLogger("enterprise_ai.seed")


def seed_sales_db():
    """Execute initial sales SQL script if sales table is missing or empty."""
    try:
        with engine.connect() as conn:
            # Check if sales table exists and has rows
            has_sales = False
            try:
                res = conn.execute(text("SELECT COUNT(*) FROM sales;")).fetchone()
                if res and res[0] > 0:
                    has_sales = True
            except Exception:
                has_sales = False

            if not has_sales:
                logger.info("Seeding sales database from 01_sales_seed.sql...")
                root_dir = Path(__file__).resolve().parents[3]
                seed_sql_path = root_dir / "data" / "sql" / "01_sales_seed.sql"
                if not seed_sql_path.exists():
                    seed_sql_path = settings.DATA_DIR / "sql" / "01_sales_seed.sql"

                if seed_sql_path.exists():
                    sql_content = seed_sql_path.read_text(encoding="utf-8")
                    # Clean up comment lines
                    clean_sql = "\n".join(
                        line for line in sql_content.splitlines()
                        if not line.strip().startswith("--")
                    )
                    statements = [s.strip() for s in clean_sql.split(";") if s.strip()]
                    with engine.begin() as tx:
                        for stmt in statements:
                            tx.execute(text(stmt))
                    logger.info("Sales database seeded successfully.")
                else:
                    logger.warning("Seed SQL file not found at %s", seed_sql_path)
            else:
                logger.info("Sales database table already seeded.")
    except Exception as err:
        logger.error("Failed to seed sales database: %s", err)


def seed_company_documents():
    """Ingest company PDF documents into PostgreSQL DocumentRecord and ChromaDB vector store."""
    try:
        root_dir = Path(__file__).resolve().parents[3]
        docs_dir = root_dir / "data" / "nexatech_documents" / "documents"
        if not docs_dir.exists():
            docs_dir = settings.DATA_DIR / "nexatech_documents" / "documents"
        if not docs_dir.exists():
            docs_dir = settings.DATA_DIR / "documents"

        if docs_dir.exists():
            logger.info("Ingesting company documents from %s...", docs_dir)
            total_chunks = ingest_documents(docs_dir)
            logger.info("Company documents ingested successfully (%d chunks total).", total_chunks)
        else:
            logger.warning("Company documents directory not found at %s", docs_dir)
    except Exception as err:
        logger.error("Failed to seed company documents: %s", err)


def seed_all():
    """Run all startup seeding procedures."""
    seed_sales_db()
    seed_company_documents()
