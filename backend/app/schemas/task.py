from __future__ import annotations

"""Sprint 1 – Task schemas.

Defines TaskProfile (canonical routing input), TaskExecution (runtime
state tracking), and supporting types for the task lifecycle.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from shared.enums import ModelCapability, TaskState


# ---------------------------------------------------------------------------
# Task type → capability mapping
# ---------------------------------------------------------------------------

# Canonical mapping of task types to their required model capabilities.
# The lifecycle manager uses this to classify tasks for routing.
TASK_TYPE_CAPABILITIES: dict[str, list[ModelCapability]] = {
    "document_analysis": [
        ModelCapability.VISION,
        ModelCapability.DOCUMENT_UNDERSTANDING,
    ],
    "code_review": [
        ModelCapability.CODING,
        ModelCapability.REASONING,
    ],
    "text_generation": [
        ModelCapability.TEXT,
    ],
    "reasoning": [
        ModelCapability.TEXT,
        ModelCapability.REASONING,
    ],
    "data_extraction": [
        ModelCapability.TEXT,
        ModelCapability.STRUCTURED_OUTPUT,
    ],
}


# ---------------------------------------------------------------------------
# Core schemas
# ---------------------------------------------------------------------------


class TaskProfile(BaseModel):
    """Canonical task input that drives the routing pipeline.

    This is the contract between task submission and the model router.
    """

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique task identifier (auto-generated UUID)",
    )
    task_type: str = Field(
        ...,
        description="Task type key (e.g. 'document_analysis', 'code_review')",
    )
    description: str = Field(
        ...,
        description="Human-readable description of the task",
    )
    required_capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="Required model capabilities (auto-derived from task_type if empty)",
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Task payload (document content, code snippet, etc.)",
    )
    priority: str = Field(
        "MEDIUM",
        description="Priority level: LOW, MEDIUM, HIGH",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Task creation timestamp",
    )


class StateTransition(BaseModel):
    """A single state transition in the task lifecycle."""

    from_state: TaskState = Field(..., description="State before transition")
    to_state: TaskState = Field(..., description="State after transition")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the transition occurred",
    )
    detail: Optional[str] = Field(
        None,
        description="Optional detail about the transition",
    )


class TaskExecution(BaseModel):
    """Runtime state of a task as it moves through the lifecycle.

    This is the primary response object returned to the frontend,
    containing the full audit trail of how a task was routed and executed.
    """

    task_id: str = Field(..., description="Task identifier")
    task_type: str = Field(..., description="Task type")
    description: str = Field(..., description="Task description")
    current_state: TaskState = Field(..., description="Current lifecycle state")
    state_history: list[StateTransition] = Field(
        default_factory=list,
        description="Ordered list of all state transitions (audit trail)",
    )
    # Routing
    selected_model_id: Optional[str] = Field(
        None, description="ID of the model selected by the router",
    )
    selected_model_name: Optional[str] = Field(
        None, description="Human-readable name of the selected model",
    )
    routing_rationale: Optional[str] = Field(
        None,
        description="Human-readable explanation of why this model was selected "
        "(judge-visible feature)",
    )
    required_capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="Capabilities required for this task",
    )
    # Execution
    model_response: Optional[str] = Field(
        None, description="The model's generated response",
    )
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When task execution began",
    )
    completed_at: Optional[datetime] = Field(
        None, description="When task execution finished",
    )
    error: Optional[str] = Field(
        None, description="Error message if the task failed",
    )


# ---------------------------------------------------------------------------
# API request schema
# ---------------------------------------------------------------------------


class TaskSubmitRequest(BaseModel):
    """Input for submitting a new task via the API."""

    task_type: str = Field(
        ...,
        description="Task type key (e.g. 'document_analysis', 'code_review')",
    )
    description: str = Field(
        ...,
        description="What the task should accomplish",
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific payload",
    )
    priority: str = Field(
        "MEDIUM",
        description="Priority level: LOW, MEDIUM, HIGH",
    )
