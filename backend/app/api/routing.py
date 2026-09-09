"""Sprint 1 – Routing API endpoint.

Provides the ``/v1/route`` endpoint that accepts a routing request
and returns the best-matching model.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.routing import RouteRequest, RouteResponse
from app.services.router import ModelRouter

router = APIRouter(tags=["routing"])

# Module-level reference set by main.py at startup via ``configure()``.
_router: ModelRouter | None = None


def configure(model_router: ModelRouter) -> None:
    """Inject the shared ModelRouter singleton into this module."""
    global _router  # noqa: PLW0603
    _router = model_router


def _get_router() -> ModelRouter:
    assert _router is not None, "routing module not configured"
    return _router


@router.post("/v1/route", response_model=RouteResponse)
def route(request: RouteRequest) -> RouteResponse:
    """Select the best model for the given routing request.

    Returns 404 if no model satisfies the requirements.
    """
    result = _get_router().route(request)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No model matches the requested capabilities",
        )
    return result
