"""Sprint 1 – Model API endpoints.

Provides CRUD for the model registry and adapter invocation endpoints
under the ``/v1/models`` prefix.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.adapters.manager import AdapterManager
from app.schemas.adapter import (
    GenerateRequest,
    GenerateResponse,
    HealthCheckResponse,
    ToolCallRequest,
    ToolCallResponse,
)
from app.schemas.model_registry import ModelRegistryEntry
from app.services.registry import ModelRegistry

router = APIRouter(prefix="/v1/models", tags=["models"])

# These module-level references are set by main.py at startup via
# ``configure()``.  This avoids circular imports and keeps the router
# self-contained.
_registry: ModelRegistry | None = None
_manager: AdapterManager | None = None


def configure(registry: ModelRegistry, manager: AdapterManager) -> None:
    """Inject shared singletons into this router module."""
    global _registry, _manager  # noqa: PLW0603
    _registry = registry
    _manager = manager


def _get_registry() -> ModelRegistry:
    assert _registry is not None, "models router not configured"
    return _registry


def _get_manager() -> AdapterManager:
    assert _manager is not None, "models router not configured"
    return _manager


# ------------------------------------------------------------------
# Registry CRUD
# ------------------------------------------------------------------


@router.post("/", status_code=201, response_model=ModelRegistryEntry)
def register_model(entry: ModelRegistryEntry) -> ModelRegistryEntry:
    """Register a new model (or overwrite an existing one)."""
    return _get_registry().register(entry)


@router.get("/", response_model=list[ModelRegistryEntry])
def list_models() -> list[ModelRegistryEntry]:
    """List all registered models."""
    return _get_registry().list_all()


@router.get("/{model_id}", response_model=ModelRegistryEntry)
def get_model(model_id: str) -> ModelRegistryEntry:
    """Get a single model by ID."""
    entry = _get_registry().get(model_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return entry


@router.delete("/{model_id}", status_code=200)
def delete_model(model_id: str) -> dict:
    """Delete a model by ID."""
    deleted = _get_registry().delete(model_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    _get_manager().remove_adapter(model_id)
    return {"deleted": model_id}


# ------------------------------------------------------------------
# Adapter invocation
# ------------------------------------------------------------------


@router.post("/{model_id}/generate", response_model=GenerateResponse)
async def generate(model_id: str, request: GenerateRequest) -> GenerateResponse:
    """Invoke non-streaming text generation on a model."""
    adapter = _get_manager().get_adapter(model_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return await adapter.generate(request)


@router.post("/{model_id}/stream")
async def stream(model_id: str, request: GenerateRequest) -> StreamingResponse:
    """Invoke streaming text generation on a model (SSE)."""
    adapter = _get_manager().get_adapter(model_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    async def _event_stream() -> AsyncIterator[str]:
        async for chunk in adapter.stream(request):
            data = json.dumps({"text": chunk.text, "finished": chunk.finished})
            yield f"data: {data}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{model_id}/tool-call", response_model=ToolCallResponse)
async def tool_call(
    model_id: str, request: ToolCallRequest
) -> ToolCallResponse:
    """Invoke tool-call selection on a model."""
    adapter = _get_manager().get_adapter(model_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return await adapter.tool_call(request)


@router.get("/{model_id}/health", response_model=HealthCheckResponse)
async def model_health(model_id: str) -> HealthCheckResponse:
    """Check health of a specific model's adapter."""
    adapter = _get_manager().get_adapter(model_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return await adapter.health_check()
