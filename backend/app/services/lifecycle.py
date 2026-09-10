from __future__ import annotations

"""Sprint 1 – Task Lifecycle Manager.

Implements the task state machine that drives a task through
INTAKE → CLASSIFY → PLAN → DELIVER for Sprint 1 (straight-line,
no branching).  Full pipeline states will be enabled in later sprints.

Each state transition is recorded in the TaskExecution's state_history
for full auditability.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.adapters.manager import AdapterManager
from app.schemas.adapter import GenerateRequest
from app.schemas.routing import RouteRequest
from app.schemas.task import (
    TASK_TYPE_CAPABILITIES,
    StateTransition,
    TaskExecution,
    TaskProfile,
)
from app.services.registry import ModelRegistry
from app.services.router import ModelRouter
from shared.enums import ModelCapability, TaskState

logger = logging.getLogger(__name__)


class TaskLifecycleManager:
    """Drives tasks through the lifecycle state machine.

    Sprint 1 pipeline (straight-line):
        INTAKE → CLASSIFY → PLAN → DELIVER

    Each step:
    - INTAKE:   receive + validate the task profile
    - CLASSIFY: map task_type to required_capabilities
    - PLAN:     route to best model, invoke model, get response
    - DELIVER:  package result with routing rationale

    Full pipeline (future sprints):
        INTAKE → CLASSIFY → PLAN → RETRIEVE → OBSERVE →
        VERIFY → APPROVE → DELIVER → AUDIT

    Args:
        registry: Model registry for lookups.
        router: Model router for selection.
        adapter_manager: Adapter manager for model invocation.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        router: ModelRouter,
        adapter_manager: AdapterManager,
    ) -> None:
        self._registry = registry
        self._router = router
        self._adapter_manager = adapter_manager
        # In-memory task store (Sprint 1)
        self._tasks: dict[str, TaskExecution] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(self, profile: TaskProfile) -> TaskExecution:
        """Run a task through the full Sprint 1 lifecycle.

        Args:
            profile: The task profile to execute.

        Returns:
            A TaskExecution with the full audit trail and result.
        """
        execution = TaskExecution(
            task_id=profile.task_id,
            task_type=profile.task_type,
            description=profile.description,
            current_state=TaskState.INTAKE,
        )

        try:
            # INTAKE → CLASSIFY
            execution = self._intake(execution, profile)
            execution = self._classify(execution, profile)
            execution = await self._plan(execution, profile)
            execution = self._deliver(execution)
        except Exception as exc:
            execution = self._transition(
                execution, TaskState.FAILED, detail=str(exc)
            )
            execution.error = str(exc)
            logger.error("Task %s failed: %s", profile.task_id, exc)

        self._tasks[profile.task_id] = execution
        return execution

    def get_task(self, task_id: str) -> Optional[TaskExecution]:
        """Retrieve a task execution by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskExecution]:
        """List all task executions."""
        return list(self._tasks.values())

    # ------------------------------------------------------------------
    # State machine steps
    # ------------------------------------------------------------------

    def _intake(
        self, execution: TaskExecution, profile: TaskProfile
    ) -> TaskExecution:
        """INTAKE: Validate and accept the task."""
        # Validate task_type
        known_types = set(TASK_TYPE_CAPABILITIES.keys())
        if profile.task_type not in known_types:
            logger.warning(
                "Unknown task type '%s', will use generic TEXT capabilities",
                profile.task_type,
            )

        logger.info(
            "Task %s: INTAKE — type=%s, priority=%s",
            profile.task_id, profile.task_type, profile.priority,
        )
        return execution  # already in INTAKE state

    def _classify(
        self, execution: TaskExecution, profile: TaskProfile
    ) -> TaskExecution:
        """CLASSIFY: Map task type to required capabilities."""
        execution = self._transition(
            execution, TaskState.CLASSIFY,
            detail=f"Classifying task type '{profile.task_type}'",
        )

        # Derive capabilities from task type
        if profile.required_capabilities:
            capabilities = profile.required_capabilities
        else:
            capabilities = TASK_TYPE_CAPABILITIES.get(
                profile.task_type,
                [ModelCapability.TEXT],  # fallback
            )

        execution.required_capabilities = capabilities

        logger.info(
            "Task %s: CLASSIFY — capabilities=%s",
            profile.task_id, [str(c) for c in capabilities],
        )
        return execution

    async def _plan(
        self, execution: TaskExecution, profile: TaskProfile
    ) -> TaskExecution:
        """PLAN: Route to model, invoke, get response."""
        execution = self._transition(
            execution, TaskState.PLAN,
            detail="Routing to best model and invoking",
        )

        # Route
        route_request = RouteRequest(
            required_capabilities=execution.required_capabilities,
            prefer_low_latency=profile.priority == "HIGH",
        )
        route_result = self._router.route(route_request)

        if route_result is None:
            raise RuntimeError(
                f"No model available for capabilities: "
                f"{[str(c) for c in execution.required_capabilities]}"
            )

        execution.selected_model_id = route_result.model_id
        execution.selected_model_name = route_result.model_name
        execution.routing_rationale = route_result.reasoning

        logger.info(
            "Task %s: PLAN — routed to model '%s' (%s). Rationale: %s",
            profile.task_id,
            route_result.model_name,
            route_result.model_id,
            route_result.reasoning,
        )

        # Invoke the model
        adapter = self._adapter_manager.get_adapter(route_result.model_id)
        if adapter is None:
            raise RuntimeError(
                f"Adapter not available for model '{route_result.model_id}'"
            )

        # Build the prompt with task context
        prompt = self._build_prompt(profile)
        gen_request = GenerateRequest(
            prompt=prompt,
            system_prompt=(
                f"You are a SAFIRE AI assistant. You have been selected for "
                f"this task because you have the following capabilities: "
                f"{', '.join(str(c) for c in route_result.capabilities)}. "
                f"Task type: {profile.task_type}."
            ),
            temperature=0.7,
        )

        response = await adapter.generate(gen_request)
        execution.model_response = response.text

        logger.info(
            "Task %s: PLAN — model response received (%d chars)",
            profile.task_id, len(response.text),
        )
        return execution

    def _deliver(self, execution: TaskExecution) -> TaskExecution:
        """DELIVER: Finalize the task with results."""
        execution = self._transition(
            execution, TaskState.DELIVER,
            detail="Task completed successfully",
        )
        execution.completed_at = datetime.now(timezone.utc)

        logger.info("Task %s: DELIVER — complete", execution.task_id)
        return execution

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _transition(
        self,
        execution: TaskExecution,
        to_state: TaskState,
        *,
        detail: Optional[str] = None,
    ) -> TaskExecution:
        """Record a state transition."""
        transition = StateTransition(
            from_state=execution.current_state,
            to_state=to_state,
            detail=detail,
        )
        execution.state_history.append(transition)
        execution.current_state = to_state
        return execution

    @staticmethod
    def _build_prompt(profile: TaskProfile) -> str:
        """Build the prompt string from a task profile."""
        parts = [profile.description]

        if profile.input_data:
            # Include relevant input data in the prompt
            for key, value in profile.input_data.items():
                if isinstance(value, str) and len(value) < 5000:
                    parts.append(f"\n--- {key} ---\n{value}")

        return "\n".join(parts)
