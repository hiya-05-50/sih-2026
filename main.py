from fastapi import FastAPI, Response
from app.core.config import settings
from app.services.registry import ModelRegistry
from app.adapters.manager import AdapterManager
from app.services.router import ModelRouter
from app.api import models as models_api
from app.api import routing as routing_api

app = FastAPI(title=settings.app_name, version="0.1.0")

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

registry = ModelRegistry()
adapter_manager = AdapterManager(registry)
model_router = ModelRouter(registry)

# Wire singletons into API router modules
models_api.configure(registry, adapter_manager)
routing_api.configure(model_router)

# Include API routers
app.include_router(models_api.router)
app.include_router(routing_api.router)

# ---------------------------------------------------------------------------
# Baseline operational endpoints
# ---------------------------------------------------------------------------

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
async def ready(response: Response):
    models = registry.list_all()
    if not models:
        response.status_code = 503
        return {
            "status": "not_ready",
            "reason": "No models registered",
        }

    health_results = await adapter_manager.health_check_all()
    healthy_count = sum(1 for r in health_results.values() if r.healthy)

    if healthy_count == 0:
        response.status_code = 503
        return {
            "status": "not_ready",
            "reason": "No healthy model adapters",
        }

    return {
        "status": "ready",
        "models_registered": len(models),
        "models_healthy": healthy_count,
    }
