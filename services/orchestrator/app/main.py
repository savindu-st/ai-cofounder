"""AI Co-Founder Monolithic Orchestrator Entrypoint."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from shared.db.session import get_db

try:
    from services.orchestrator.app.api.routes import router as api_router
    from services.orchestrator.app.api.stream import router as stream_router
except ImportError:
    from app.api.routes import router as api_router
    from app.api.stream import router as stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: Idempotent ChromaDB vector store seeding on startup."""
    try:
        from shared.db.session import init_db
        await init_db()
    except Exception as exc:
        print(f"[Startup Warning] Database initialization failed: {exc}")

    persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
    try:
        import sys
        import os
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        from services.business_intelligence.app.rag.seed_vector_store import seed_chromadb_if_empty
        seed_chromadb_if_empty(persist_directory=persist_dir)
    except Exception as exc:
        print(f"[Startup Warning] Vector store seeding skipped: {exc}")
    yield


app = FastAPI(
    title="AI Co-Founder Orchestrator",
    description="Central LangGraph stateful multi-agent orchestration backend",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(stream_router, prefix="/api")


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unknown"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {e}"
    
    return {"status": "healthy", "service": "orchestrator", "db": db_status, "topology": "monolith"}
