from __future__ import annotations

"""Sprint 3 – Tool Registry.

Provides the schema and centralized registry for all agent tools.
Enforces PRD §19 constraints (permissions, risk, network, limits).
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from shared.enums import RiskLevel, UserRole

logger = logging.getLogger(__name__)


class ToolResourceLimits(BaseModel):
    """Resource constraints for tool execution."""
    max_memory_mb: int = Field(default=256, ge=64, le=1024)
    max_cpu_cores: float = Field(default=1.0, ge=0.1, le=4.0)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    network_access: bool = Field(default=False)


class ToolDefinition(BaseModel):
    """A tool's definition and metadata per PRD §19."""
    name: str = Field(..., max_length=64)
    description: str = Field(..., max_length=512)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # PRD §19 specific fields
    risk_level: RiskLevel = Field(default=RiskLevel.GREEN)
    required_role: UserRole = Field(default=UserRole.ENGINEER)
    resource_limits: ToolResourceLimits = Field(default_factory=ToolResourceLimits)
    audit_required: bool = Field(default=True)
    
    # Internal execution
    handler: Optional[Callable] = Field(None, exclude=True)


class ToolRegistry:
    """Centralized registry for all available agent tools."""
    
    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        """Register a new tool."""
        if tool_def.name in self._tools:
            logger.warning(f"Tool {tool_def.name} is already registered. Overwriting.")
        self._tools[tool_def.name] = tool_def
        logger.info(f"Registered tool: {tool_def.name}")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())
        
    def to_adapter_format(self) -> List[Dict[str, Any]]:
        """Convert registry contents to the format expected by ModelAdapter."""
        result = []
        for t in self._tools.values():
            result.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            })
        return result
