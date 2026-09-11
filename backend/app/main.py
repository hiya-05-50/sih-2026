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
# Sprint 5 services
from app.services.audit import AuditEventStore
from app.services.sovereignty import SovereigntyMonitor
from app.services.siab import SIABRunner
from app.api import models as models_api
from app.api import routing as routing_api
from app.api import tasks as tasks_api
from app.api import benchmark as benchmark_api
from app.api import documents as documents_api
from app.api import approval as approval_api
from app.api import artifacts as artifacts_api
from app.api import flagship as flagship_api
# Sprint 5 API modules
from app.api import audit as audit_api
from app.api import sovereignty as sovereignty_api
from app.api import siab as siab_api
# Sprint 6 API modules
from app.api import demo as demo_api

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

# Sprint 5 services
audit_store = AuditEventStore()
sovereignty_monitor = SovereigntyMonitor(audit_store=audit_store)
siab_runner = SIABRunner(audit_store=audit_store)

# Sprint 4 services (with Sprint 6 integration)
approval_service = ApprovalService()
flagship_pipeline = FlagshipPipeline(
    adapter_manager,
    approval_service,
    audit_store=audit_store,
    sovereignty_monitor=sovereignty_monitor,
    model_router=model_router,
)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: seed models at startup."""
    count = await seed_models(registry)
    logger.info("Startup complete: %d model(s) seeded", count)
    # Sprint 5: Run sovereignty self-test on startup
    sovereignty_status = sovereignty_monitor.check_sovereignty()
    logger.info(
        "Sovereignty status: %s — %s",
        sovereignty_status.state, sovereignty_status.detail,
    )
    yield
    logger.info("Shutting down SAFIRE backend")


app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
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
# Sprint 5 wiring
audit_api.configure(audit_store)
sovereignty_api.configure(sovereignty_monitor)
siab_api.configure(siab_runner)
# Sprint 6 wiring
demo_api.configure(flagship_pipeline, audit_store, sovereignty_monitor)

# Include API routers
app.include_router(models_api.router)
app.include_router(routing_api.router)
app.include_router(tasks_api.router)
app.include_router(benchmark_api.router)
app.include_router(documents_api.router)
app.include_router(approval_api.router)
app.include_router(artifacts_api.router)
app.include_router(flagship_api.router)
# Sprint 5 routers
app.include_router(audit_api.router)
app.include_router(sovereignty_api.router)
app.include_router(siab_api.router)
# Sprint 6 routers
app.include_router(demo_api.router)


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
