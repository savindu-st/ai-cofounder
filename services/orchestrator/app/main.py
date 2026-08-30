from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.api.stream import router as stream_router

app = FastAPI(
    title="AI Co-Founder Orchestrator",
    description="Central LangGraph stateful multi-agent orchestration backend",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(stream_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "orchestrator"}
