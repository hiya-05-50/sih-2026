import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.registry import ModelRegistry
from app.adapters.manager import AdapterManager
from app.services.router import ModelRouter
from app.services.lifecycle import TaskLifecycleManager
from app.services.benchmark import BenchmarkRunner
from app.services.seed import seed_models
from app.services.tools.registry import ToolRegistry
from app.services.tools.implementations import register_all_tools
from app.services.approval import ApprovalService
from app.services.flagship_pipeline import FlagshipPipeline
from app.api import models as models_api
from app.api import routing as routing_api
from app.api import tasks as tasks_api
from app.api import benchmark as benchmark_api
from app.api import documents as documents_api
from app.api import approval as approval_api
from app.api import artifacts as artifacts_api
from app.api import flagship as flagship_api

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

registry = ModelRegistry()
adapter_manager = AdapterManager(registry)
model_router = ModelRouter(registry)
lifecycle_manager = TaskLifecycleManager(registry, model_router, adapter_manager)
benchmark_runner = BenchmarkRunner(registry, adapter_manager)

# Sprint 3 tools
tool_registry = ToolRegistry()
register_all_tools(tool_registry)

# Sprint 4 services
approval_service = ApprovalService()
flagship_pipeline = FlagshipPipeline(adapter_manager, approval_service)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: seed models at startup."""
    count = await seed_models(registry)
    logger.info("Startup complete: %d model(s) seeded", count)
    yield
    logger.info("Shutting down SAFIRE backend")


app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS (allow frontend)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Wire singletons into API router modules
# ---------------------------------------------------------------------------

models_api.configure(registry, adapter_manager)
routing_api.configure(model_router)
tasks_api.configure(lifecycle_manager)
benchmark_api.configure(benchmark_runner)
documents_api.configure(adapter_manager, tool_registry)
approval_api.configure(approval_service)
artifacts_api.configure(flagship_pipeline)
flagship_api.configure(flagship_pipeline)

# Include API routers
app.include_router(models_api.router)
app.include_router(routing_api.router)
app.include_router(tasks_api.router)
app.include_router(benchmark_api.router)
app.include_router(documents_api.router)
app.include_router(approval_api.router)
app.include_router(artifacts_api.router)
app.include_router(flagship_api.router)


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

