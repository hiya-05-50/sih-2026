from __future__ import annotations

"""Sprint 5 – Audit Event & Sovereignty Status Schemas.

Defines the structured event contracts for:
  - AuditEvent: immutable record of any significant system action
  - SovereigntyStatus: backend-derived sovereignty readiness state
  - SovereigntyCheckResult: individual sovereignty self-test result
  - BlockedAttempt: record of a blocked external call / policy violation
"""

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.enums import SovereigntyState, UserRole


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------


class AuditEventType(StrEnum):
    """Canonical audit event types for SAFIRE."""

    TASK_CREATED = "TASK_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    MODEL_SELECTED = "MODEL_SELECTED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_BLOCKED = "TOOL_BLOCKED"
    VERIFICATION_RUN = "VERIFICATION_RUN"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_DECIDED = "APPROVAL_DECIDED"
    ARTIFACT_GENERATED = "ARTIFACT_GENERATED"
    ARTIFACT_VALIDATED = "ARTIFACT_VALIDATED"
    SOVEREIGNTY_CHECK = "SOVEREIGNTY_CHECK"
    SOVEREIGNTY_BLOCKED = "SOVEREIGNTY_BLOCKED"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    DOCUMENT_INGESTED = "DOCUMENT_INGESTED"


class AuditSeverity(StrEnum):
    """Severity levels for audit events."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AuditEvent(BaseModel):
    """Immutable record of a significant system action."""

    event_id: str = Field(
        default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}",
        description="Unique event identifier",
    )
    event_type: AuditEventType = Field(
        ..., description="Type of audit event"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp",
    )
    actor: str = Field(
        default="system",
        description="User ID or 'system' for automated actions",
    )
    actor_role: Optional[UserRole] = Field(
        None, description="Role of the actor if applicable"
    )
    task_id: Optional[str] = Field(
        None, description="Associated task ID if applicable"
    )
    detail: str = Field(
        "", description="Human-readable description of the event"
    )
    severity: AuditSeverity = Field(
        default=AuditSeverity.INFO, description="Event severity"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured metadata",
    )


# ---------------------------------------------------------------------------
# Sovereignty
# ---------------------------------------------------------------------------


class SovereigntyCheckResult(BaseModel):
    """Result of an individual sovereignty self-test check."""

    check_name: str = Field(..., description="Name of the check")
    passed: bool = Field(..., description="Whether the check passed")
    detail: str = Field("", description="Human-readable explanation")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


class BlockedAttempt(BaseModel):
    """Record of a blocked external call or policy violation."""

    attempt_id: str = Field(
        default_factory=lambda: f"blk-{uuid.uuid4().hex[:8]}",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    source: str = Field(
        ..., description="Component that attempted the external call"
    )
    destination: str = Field(
        ..., description="Target host/URL that was blocked"
    )
    reason: str = Field(
        ..., description="Why it was blocked"
    )
    action_taken: str = Field(
        default="BLOCKED", description="Action taken (BLOCKED, LOGGED, etc.)"
    )


class SovereigntyStatus(BaseModel):
    """Backend-derived sovereignty readiness state.

    This is THE source of truth for sovereignty status displayed in the UI.
    The UI must never display a 'READY' state unless the backend has
    actually established that state through self-test.
    """

    state: SovereigntyState = Field(
        default=SovereigntyState.NOT_READY,
        description="Current sovereignty state",
    )
    checks: List[SovereigntyCheckResult] = Field(
        default_factory=list,
        description="Results of individual sovereignty checks",
    )
    blocked_attempts: List[BlockedAttempt] = Field(
        default_factory=list,
        description="Recent blocked external call attempts",
    )
    external_connections: int = Field(
        default=0, description="Number of detected external connections"
    )
    external_dns_queries: int = Field(
        default=0, description="Number of detected external DNS queries"
    )
    cloud_api_calls: int = Field(
        default=0, description="Number of detected cloud API calls"
    )
    last_check_at: Optional[str] = Field(
        None, description="Timestamp of the last sovereignty check"
    )
    detail: str = Field(
        "", description="Human-readable summary of sovereignty status"
    )
