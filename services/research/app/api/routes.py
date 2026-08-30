from fastapi import FastAPI
app = FastAPI(title="Research & Critic Service")

@app.get("/health")
def health():
    return {"service": "research", "status": "healthy"}
