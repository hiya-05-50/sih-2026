from __future__ import annotations

"""Sprint 5 – Sovereignty API Endpoints.

Provides ``/v1/sovereignty`` endpoints for the sovereignty dashboard.
The frontend MUST use this as the source of truth for sovereignty status —
it must NEVER display a green/verified state unless this API reports READY.
"""

from typing import List

from fastapi import APIRouter

from app.schemas.audit import BlockedAttempt, SovereigntyStatus
from app.services.sovereignty import SovereigntyMonitor

router = APIRouter(prefix="/v1/sovereignty", tags=["sovereignty"])

_monitor: SovereigntyMonitor | None = None


def configure(monitor: SovereigntyMonitor) -> None:
    """Inject the shared SovereigntyMonitor singleton."""
    global _monitor
    _monitor = monitor


def _get_monitor() -> SovereigntyMonitor:
    assert _monitor is not None, "sovereignty router not configured"
    return _monitor


@router.get("/status", response_model=SovereigntyStatus)
async def get_sovereignty_status() -> SovereigntyStatus:
    """Get the current sovereignty status.

    This is the backend-derived source of truth.  The UI must use this
    endpoint to determine what sovereignty state to display.
    """
    return _get_monitor().get_status()


@router.post("/self-test", response_model=SovereigntyStatus)
async def run_sovereignty_self_test() -> SovereigntyStatus:
    """Trigger a sovereignty self-test.

    Performs real checks:
      1. External TCP connectivity (must fail)
      2. External DNS resolution (must fail)
      3. API binding locality (must be localhost)
      4. Sandbox network isolation (must be --network none)
    """
    return _get_monitor().check_sovereignty()


@router.get("/blocked", response_model=List[BlockedAttempt])
async def list_blocked_attempts() -> List[BlockedAttempt]:
    """List all recorded blocked external call attempts."""
    return _get_monitor().get_blocked_attempts()
