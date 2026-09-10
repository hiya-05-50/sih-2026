from __future__ import annotations

"""Sprint 3 – Tool Implementations.

Provides implementations for P0 standard tools and registers them.
"""

from typing import Any, Dict

from app.services.tools.registry import ToolDefinition, ToolRegistry
from app.services.tools.sandbox import get_run_python_tool
from shared.enums import RiskLevel, UserRole


def calculate(expression: str) -> Dict[str, Any]:
    """Stub implementation of calculate."""
    return {"result": f"Simulated result for {expression}"}


def search_knowledge(query: str) -> Dict[str, Any]:
    """Stub implementation of search_knowledge."""
    return {"results": [f"Simulated retrieval for: {query}"]}


def register_all_tools(registry: ToolRegistry) -> None:
    """Populate the registry with all available Sprint 3 tools."""
    
    # 1. Python Sandbox
    registry.register(get_run_python_tool())
    
    # 2. Calculate
    registry.register(ToolDefinition(
        name="calculate",
        description="Perform basic math calculations.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression (e.g., '2 + 2')."
                }
            },
            "required": ["expression"]
        },
        handler=calculate
    ))
    
    # 3. Search Knowledge
    registry.register(ToolDefinition(
        name="search_knowledge",
        description="Search ingested Evidence objects and knowledge base.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term."
                }
            },
            "required": ["query"]
        },
        handler=search_knowledge
    ))

    # We will add create_docx, extract_table, etc. here as needed
