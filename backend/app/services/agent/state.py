from __future__ import annotations

"""Sprint 3 – Agent State models.

Defines the mutable state carried across the custom async state machine loop.
Enforces tracking for MAX_AGENT_STEPS, MAX_TOOL_CALLS, MAX_RETRIES, etc.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.adapter import ToolCallResult
from shared.enums import TaskState, VerificationOutcome


class AgentExecutionBounds(BaseModel):
    """PRD §15 Enforcement bounds for the agent loop."""
    max_agent_steps: int = Field(default=10, ge=1, le=50)
    max_tool_calls: int = Field(default=10, ge=1, le=50)
    max_retries: int = Field(default=3, ge=0, le=10)
    max_execution_time_seconds: int = Field(default=300, ge=10, le=1800)


class AgentMessage(BaseModel):
    """A single message in the agent's context history."""
    role: str
    content: str
    tool_calls: Optional[List[ToolCallResult]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class AgentState(BaseModel):
    """The full mutable state of a running agent task."""
    task_id: str
    current_state: TaskState = TaskState.INTAKE
    
    # Context History
    messages: List[AgentMessage] = Field(default_factory=list)
    
    # Execution Tracking
    step_count: int = 0
    tool_call_count: int = 0
    retry_count: int = 0
    escalation_count: int = 0
    
    # Time Tracking
    start_time: float = Field(default_factory=time.time)
    
    # Loop bounds
    bounds: AgentExecutionBounds = Field(default_factory=AgentExecutionBounds)
    
    # Final outputs
    verification_outcome: Optional[VerificationOutcome] = None
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    
    def check_bounds(self) -> None:
        """Evaluate if any execution bounds have been exceeded. Raises ValueError if so."""
        if self.step_count >= self.bounds.max_agent_steps:
            raise ValueError(f"Execution bound exceeded: max_agent_steps ({self.bounds.max_agent_steps})")
        if self.tool_call_count >= self.bounds.max_tool_calls:
            raise ValueError(f"Execution bound exceeded: max_tool_calls ({self.bounds.max_tool_calls})")
        if self.retry_count >= self.bounds.max_retries:
            raise ValueError(f"Execution bound exceeded: max_retries ({self.bounds.max_retries})")
        
        elapsed = time.time() - self.start_time
        if elapsed >= self.bounds.max_execution_time_seconds:
            raise ValueError(f"Execution bound exceeded: max_execution_time ({self.bounds.max_execution_time_seconds}s)")
