from __future__ import annotations

"""Sprint 5 – Audit Event Store.

Provides a structured, queryable audit trail for all significant SAFIRE
system events.  Replaces ad-hoc `logging.info()` calls with typed
AuditEvent records that can be queried via the `/v1/audit` API.

Design decisions:
  - In-memory store for MVP (matches existing pattern in approval, lifecycle)
  - Thread-safe append-only list
  - Each event is immutable after creation
  - Events are never deleted (append-only for integrity)
"""

import logging
import threading
from typing import Dict, List, Optional

from app.schemas.audit import AuditEvent, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)


class AuditEventStore:
    """Append-only store for structured audit events.

    All significant SAFIRE actions — task lifecycle, model routing,
    tool calls, verification, approval, sovereignty, security — are
    recorded here as typed events with full traceability.
    """

    def __init__(self) -> None:
        self._events: List[AuditEvent] = []
        self._lock = threading.Lock()

    def record(
        self,
        event_type: AuditEventType,
        *,
        detail: str = "",
        actor: str = "system",
        actor_role: Optional[str] = None,
        task_id: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        metadata: Optional[Dict] = None,
    ) -> AuditEvent:
        """Record a new audit event.

        Args:
            event_type: The type of event being recorded.
            detail: Human-readable description.
            actor: User ID or 'system'.
            actor_role: Role of the actor (ENGINEER/APPROVER/ADMIN).
            task_id: Associated task ID if applicable.
            severity: Event severity level.
            metadata: Additional structured data.

        Returns:
            The created AuditEvent.
        """
        from shared.enums import UserRole

        event = AuditEvent(
            event_type=event_type,
            detail=detail,
            actor=actor,
            actor_role=UserRole(actor_role) if actor_role else None,
            task_id=task_id,
            severity=severity,
            metadata=metadata or {},
        )

        with self._lock:
            self._events.append(event)

        # Also emit to Python logging for backward compatibility
        log_level = {
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }.get(severity, logging.INFO)

        logger.log(
            log_level,
            "AUDIT [%s] %s: %s (actor=%s, task=%s)",
            severity,
            event_type,
            detail,
            actor,
            task_id,
        )

        return event

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """Retrieve a specific event by ID."""
        with self._lock:
            for event in self._events:
                if event.event_id == event_id:
                    return event
        return None

    def list_events(
        self,
        *,
        event_type: Optional[AuditEventType] = None,
        task_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        actor: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """List audit events with optional filters.

        Args:
            event_type: Filter by event type.
            task_id: Filter by task ID.
            severity: Filter by severity.
            actor: Filter by actor.
            limit: Maximum number of events to return.

        Returns:
            List of matching events, most recent first.
        """
        with self._lock:
            filtered = list(self._events)

        if event_type is not None:
            filtered = [e for e in filtered if e.event_type == event_type]
        if task_id is not None:
            filtered = [e for e in filtered if e.task_id == task_id]
        if severity is not None:
            filtered = [e for e in filtered if e.severity == severity]
        if actor is not None:
            filtered = [e for e in filtered if e.actor == actor]

        # Most recent first
        filtered.reverse()
        return filtered[:limit]

    def count_by_type(self, event_type: AuditEventType) -> int:
        """Count events of a given type."""
        with self._lock:
            return sum(1 for e in self._events if e.event_type == event_type)

    def get_security_events(self) -> List[AuditEvent]:
        """Get all security-related events."""
        security_types = {
            AuditEventType.TOOL_BLOCKED,
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.PROMPT_INJECTION_DETECTED,
            AuditEventType.SOVEREIGNTY_BLOCKED,
        }
        with self._lock:
            return [e for e in self._events if e.event_type in security_types]

    @property
    def total_events(self) -> int:
        """Total number of recorded events."""
        with self._lock:
            return len(self._events)
