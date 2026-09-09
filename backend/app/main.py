from fastapi import FastAPI, Response
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

@app.get("/")
def read_root():
    return {
        "name": settings.app_name,
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready(response: Response):
    response.status_code = 503
    return {
        "status": "not_ready",
        "reason": "Readiness dependencies are not yet implemented"
    }
