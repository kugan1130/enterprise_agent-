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
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.core.middleware import CorrelationIdMiddleware, enterprise_exception_handler
from backend.app.llm.groq_provider import GroqProvider
from backend.app.llm.llm_client import LLMClient
from backend.services.chat_service import ChatService

frontend_dir = project_dir / "frontend"


def create_app() -> FastAPI:
    # Initialize DB tables with fallback protection
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as err:
        print(f"Database table initialization notice: {err}")

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
