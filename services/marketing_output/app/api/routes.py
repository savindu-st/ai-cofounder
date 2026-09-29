from fastapi import FastAPI
app = FastAPI(title="Marketing & Document Export Service")

@app.get("/health")
def health():
    return {"service": "marketing_output", "status": "healthy"}
