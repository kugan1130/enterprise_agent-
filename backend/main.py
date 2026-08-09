import sys
from pathlib import Path

# Allow this module to run directly with `python backend/main.py`.
project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.auth import router as auth_router
from backend.app.api.chat import router as chat_router
from backend.app.api.documents import router as documents_router
from backend.app.api.health import router as health_router
from backend.app.api.reports import router as reports_router

from backend.app.core.config import settings
from backend.app.core.database import Base, SessionLocal, engine
from backend.app.core.middleware import CorrelationIdMiddleware, enterprise_exception_handler
from backend.app.llm.groq_provider import GroqProvider
from backend.app.llm.llm_client import LLMClient
from backend.services.chat_service import ChatService

frontend_dir = project_dir / "frontend"


def _ensure_document_record_columns():
    """Adds ingestion metadata columns to existing deployments without replacing document records."""
    from sqlalchemy import inspect, text

    required_columns = {
        "user_id": "INTEGER",
        "original_filename": "VARCHAR(255)",
        "file_type": "VARCHAR(50)",
        "storage_path": "VARCHAR(512)",
        "rag_status": "VARCHAR(50)",
        "sql_status": "VARCHAR(50)",
        "sql_table_name": "VARCHAR(100)",
        "error_message": "TEXT",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP"
    }
    with engine.begin() as conn:
        existing_columns = {column["name"] for column in inspect(conn).get_columns("document_records")}
        for name, column_type in required_columns.items():
            if name not in existing_columns:
                conn.execute(text(f"ALTER TABLE document_records ADD COLUMN {name} {column_type}"))
                if name in ("created_at", "updated_at"):
                    conn.execute(text(f"UPDATE document_records SET {name} = upload_timestamp WHERE {name} IS NULL"))
                
        # Reconcile legacy documents that were just given the 'processing' default
        try:
            conn.execute(text("UPDATE document_records SET status = 'indexed' WHERE status = 'processing' AND (chunk_count IS NULL OR chunk_count > 0)"))
        except Exception as e:
            pass


def _seed_sales_table_if_needed():
    """Seeds sales table from data/sql/01_sales_seed.sql if sales table does not exist or is empty."""
    try:
        from sqlalchemy import inspect, text
        with engine.connect() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            table_empty = False
            if "sales" in tables:
                row_count = conn.execute(text("SELECT COUNT(*) FROM sales")).scalar_one()
                table_empty = row_count == 0

            if "sales" not in tables or table_empty:
                sql_path = project_dir / "data" / "sql" / "01_sales_seed.sql"
                if sql_path.exists():
                    print(f"Seeding database from {sql_path.name}...")
                    sql_content = sql_path.read_text(encoding="utf-8")
                    # Remove line comments so the leading script header does not hide CREATE TABLE.
                    sql_without_comments = "\n".join(
                        line for line in sql_content.splitlines() if not line.lstrip().startswith("--")
                    )
                    statements = [s.strip() for s in sql_without_comments.split(";") if s.strip()]
                    for stmt in statements:
                        conn.execute(text(stmt))
                    conn.commit()
                    print("Successfully seeded 'sales' table with 35 transactions.")
    except Exception as err:
        print(f"Sales table seeding notice: {err}")


def _auto_ingest_initial_documents():
    """Synchronizes bundled company PDFs through the same pipeline as uploaded PDFs."""
    try:
        from backend.app.rag.ingest import COLLECTION_NAME, ingest_documents
        doc_dir = Path("/app/data/documents")
        if not doc_dir.exists():
            doc_dir = Path("/app/data/nexatech_documents/documents")
        if not doc_dir.exists():
            doc_dir = project_dir / "data" / "nexatech_documents" / "documents"

        if doc_dir.exists():
            with SessionLocal() as session:
                count = ingest_documents(doc_dir, db=session)
            print(f"Synchronized {count} chunks into Chroma collection '{COLLECTION_NAME}'")
    except Exception as err:
        print(f"Startup document ingestion notice: {err}")


def create_app() -> FastAPI:
    # Initialize DB tables with fallback protection
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_document_record_columns()
        _seed_sales_table_if_needed()
    except Exception as err:
        print(f"Database table initialization notice: {err}")

    # Auto-ingest static PDFs if Chroma collection is empty
    _auto_ingest_initial_documents()

    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

    # CORS Middleware
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID & Exception handling
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(Exception, enterprise_exception_handler)

    provider = GroqProvider()
    llm_client = LLMClient(provider)
    app.state.chat_service = ChatService(llm_client)

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(reports_router)

    dist_dir = frontend_dir / "dist"
    if dist_dir.exists():
        if (dist_dir / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        def read_root():
            return FileResponse(str(dist_dir / "index.html"))
    elif frontend_dir.exists():
        @app.get("/", include_in_schema=False)
        def read_root():
            return FileResponse(str(frontend_dir / "index.html"))

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
