from __future__ import annotations

"""Sprint 5 – Audit API Endpoints.

Provides ``/v1/audit`` endpoints for querying the structured audit trail.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.audit import AuditEvent, AuditEventType, AuditSeverity
from app.services.audit import AuditEventStore

router = APIRouter(prefix="/v1/audit", tags=["audit"])

_audit_store: AuditEventStore | None = None


def configure(audit_store: AuditEventStore) -> None:
    """Inject the shared AuditEventStore singleton."""
    global _audit_store
    _audit_store = audit_store


def _get_store() -> AuditEventStore:
    assert _audit_store is not None, "audit router not configured"
    return _audit_store


@router.get("/", response_model=List[AuditEvent])
async def list_audit_events(
    event_type: Optional[AuditEventType] = None,
    task_id: Optional[str] = None,
    severity: Optional[AuditSeverity] = None,
    limit: int = 100,
) -> List[AuditEvent]:
    """List audit events with optional filters.

    Returns events in reverse chronological order (most recent first).
    """
    store = _get_store()
    return store.list_events(
        event_type=event_type,
        task_id=task_id,
        severity=severity,
        limit=limit,
    )


@router.get("/security", response_model=List[AuditEvent])
async def list_security_events() -> List[AuditEvent]:
    """List all security-related audit events.

    Includes: TOOL_BLOCKED, SECURITY_VIOLATION, PROMPT_INJECTION_DETECTED,
    SOVEREIGNTY_BLOCKED.
    """
    return _get_store().get_security_events()


@router.get("/{event_id}", response_model=AuditEvent)
async def get_audit_event(event_id: str) -> AuditEvent:
    """Get a specific audit event by ID."""
    event = _get_store().get_event(event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Audit event '{event_id}' not found",
        )
    return event
