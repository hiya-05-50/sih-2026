from __future__ import annotations

"""Sprint 3+5 – Custom Async State Machine for Agent Execution.

Implements a deterministic state machine for the TaskState lifecycle.
Enforces execution bounds aggressively.

Sprint 5 additions:
  - Tool permission enforcement (role-based, per PRD §19/§24)
  - Audit event integration for tool calls and blocked actions
"""

import logging
from typing import Optional

from app.adapters.base import ModelAdapter
from app.schemas.adapter import GenerateRequest, ToolCallRequest, ToolCallResult
from app.services.agent.state import AgentState, AgentMessage
from app.services.tools.registry import ToolRegistry
from shared.enums import TaskState, UserRole, VerificationOutcome

logger = logging.getLogger(__name__)

# Role hierarchy for permission checks
_ROLE_HIERARCHY = {
    UserRole.ADMIN: 3,
    UserRole.APPROVER: 2,
    UserRole.ENGINEER: 1,
}


class AgentLoop:
    """Executes a single task through the SAFIRE lifecycle states."""

    def __init__(
        self,
        task_id: str,
        adapter: ModelAdapter,
        registry: ToolRegistry,
        *,
        user_role: UserRole = UserRole.ENGINEER,
        audit_store=None,
    ) -> None:
        self.state = AgentState(task_id=task_id)
        self.adapter = adapter
        self.registry = registry
        self.user_role = user_role
        self._audit_store = audit_store

    async def run(self) -> AgentState:
        """Run the state machine until completion or failure."""
        logger.info(f"Starting agent loop for task {self.state.task_id}")
        
        try:
            while self.state.current_state not in (TaskState.DELIVER, TaskState.FAILED, TaskState.AUDIT):
                self.state.check_bounds()
                self.state.step_count += 1
                
                logger.info(f"Task {self.state.task_id} entering state: {self.state.current_state}")
                
                # State transition logic
                if self.state.current_state == TaskState.INTAKE:
                    await self._handle_intake()
                elif self.state.current_state == TaskState.CLASSIFY:
                    await self._handle_classify()
                elif self.state.current_state == TaskState.PLAN:
                    await self._handle_plan()
                elif self.state.current_state == TaskState.RETRIEVE:
                    await self._handle_retrieve_or_tool()
                elif self.state.current_state == TaskState.OBSERVE:
                    await self._handle_observe()
                elif self.state.current_state == TaskState.VERIFY:
                    await self._handle_verify()
                elif self.state.current_state == TaskState.APPROVE:
                    await self._handle_approve()
                else:
                    raise ValueError(f"Unhandled state: {self.state.current_state}")

        except Exception as e:
            logger.error(f"Agent loop failed: {e}")
            self.state.error_message = str(e)
            self.state.current_state = TaskState.FAILED
            
        return self.state

    # --- Permission Enforcement ---

    def _check_tool_permission(
        self, tool_name: str, required_role: UserRole
    ) -> bool:
        """Check if the current user's role meets the tool's requirement.

        Returns True if permitted, False if blocked.
        """
        user_level = _ROLE_HIERARCHY.get(self.user_role, 0)
        required_level = _ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level

    def _record_tool_blocked(
        self, tool_name: str, required_role: UserRole
    ) -> None:
        """Record a TOOL_BLOCKED audit event."""
        if self._audit_store is not None:
            from app.schemas.audit import AuditEventType, AuditSeverity
            self._audit_store.record(
                AuditEventType.TOOL_BLOCKED,
                detail=(
                    f"Tool '{tool_name}' blocked: user role {self.user_role} "
                    f"insufficient (requires {required_role})"
                ),
                actor="agent",
                actor_role=str(self.user_role),
                task_id=self.state.task_id,
                severity=AuditSeverity.WARNING,
                metadata={
                    "tool_name": tool_name,
                    "user_role": str(self.user_role),
                    "required_role": str(required_role),
                },
            )

    def _record_tool_called(self, tool_name: str) -> None:
        """Record a TOOL_CALLED audit event."""
        if self._audit_store is not None:
            from app.schemas.audit import AuditEventType
            self._audit_store.record(
                AuditEventType.TOOL_CALLED,
                detail=f"Tool '{tool_name}' executed by {self.user_role}",
                actor="agent",
                actor_role=str(self.user_role),
                task_id=self.state.task_id,
                metadata={"tool_name": tool_name},
            )

    # --- State Handlers ---

    async def _handle_intake(self) -> None:
        """Validate input and setup context."""
        # For Vertical Slice V1, we assume intake is already pre-seeded.
        self.state.current_state = TaskState.CLASSIFY

    async def _handle_classify(self) -> None:
        """Determine task routing and requirements."""
        self.state.current_state = TaskState.PLAN

    async def _handle_plan(self) -> None:
        """Formulate a step-by-step plan."""
        # We can ask the model to plan or go straight to retrieving
        self.state.current_state = TaskState.RETRIEVE

    async def _handle_retrieve_or_tool(self) -> None:
        """Model decides to call tools or proceed."""
        # Convert state messages to tool call request
        prompt = "\n".join([m.content for m in self.state.messages])
        if not prompt:
            prompt = "Begin task."

        request = ToolCallRequest(
            prompt=prompt,
            tools=self.registry.to_adapter_format()
        )
        
        response = await self.adapter.tool_call(request)
        
        if not response.tool_calls or response.tool_calls[0].tool_name == "fallback":
            # Model decided not to use tools
            fallback_msg = response.tool_calls[0].arguments.get("model_response", "No tool call") if response.tool_calls else "No tools used"
            self.state.messages.append(AgentMessage(role="assistant", content=fallback_msg))
            self.state.current_state = TaskState.OBSERVE
            return
            
        self.state.tool_call_count += 1
        
        # Execute the first tool called (simulating linear execution for now)
        tool_call = response.tool_calls[0]
        tool_def = self.registry.get_tool(tool_call.tool_name)
        
        if not tool_def or not tool_def.handler:
            error_msg = f"Unknown or unexecutable tool: {tool_call.tool_name}"
            self.state.messages.append(AgentMessage(role="system", content=error_msg))
            logger.warning(error_msg)
        else:
            # --- Sprint 5: Tool permission enforcement ---
            if not self._check_tool_permission(tool_call.tool_name, tool_def.required_role):
                blocked_msg = (
                    f"BLOCKED: Tool '{tool_call.tool_name}' requires role "
                    f"{tool_def.required_role}, but user has role {self.user_role}. "
                    f"Access denied per SAFIRE least-privilege policy."
                )
                self.state.messages.append(
                    AgentMessage(role="system", content=blocked_msg)
                )
                self._record_tool_blocked(tool_call.tool_name, tool_def.required_role)
                logger.warning(blocked_msg)
            else:
                try:
                    # Execute tool
                    result = tool_def.handler(**tool_call.arguments)
                    self.state.messages.append(AgentMessage(
                        role="tool", 
                        content=str(result),
                        name=tool_call.tool_name
                    ))
                    self._record_tool_called(tool_call.tool_name)
                except Exception as e:
                    self.state.messages.append(AgentMessage(role="tool", content=f"Error executing {tool_call.tool_name}: {e}"))
                
        # Move to observe the result
        self.state.current_state = TaskState.OBSERVE

    async def _handle_observe(self) -> None:
        """Process tool results."""
        self.state.current_state = TaskState.VERIFY

    async def _handle_verify(self) -> None:
        """Verify task completion."""
        # Stub for V1/V2
        self.state.verification_outcome = VerificationOutcome.PASS
        self.state.current_state = TaskState.APPROVE

    async def _handle_approve(self) -> None:
        """Wait for human approval if needed."""
        self.state.current_state = TaskState.DELIVER
