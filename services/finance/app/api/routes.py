from fastapi import FastAPI
app = FastAPI(title="Finance Service")

@app.get("/health")
def health():
    return {"service": "finance", "status": "healthy"}
