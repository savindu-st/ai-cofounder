from fastapi import FastAPI
app = FastAPI(title="Business Intelligence Service")

@app.get("/health")
def health():
    return {"service": "business-intelligence", "status": "healthy"}
