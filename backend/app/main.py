from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

@app.get("/")
def read_root():
    return {
        "name": settings.app_name,
        "status": "running"
    }
