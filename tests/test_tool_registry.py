import pytest
from app.services.tools.registry import ToolRegistry, ToolDefinition, ToolResourceLimits
from shared.enums import RiskLevel, UserRole

def test_tool_registry_registration():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="test_tool",
        description="A test tool",
        risk_level=RiskLevel.GREEN,
        required_role=UserRole.ENGINEER
    )
    
    registry.register(tool)
    
    retrieved = registry.get_tool("test_tool")
    assert retrieved is not None
    assert retrieved.name == "test_tool"
    assert len(registry.list_tools()) == 1

def test_tool_registry_to_adapter_format():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="calc",
        description="Calculate things",
        parameters={"type": "object"}
    )
    registry.register(tool)
    
    formatted = registry.to_adapter_format()
    assert len(formatted) == 1
    assert formatted[0]["name"] == "calc"
    assert formatted[0]["description"] == "Calculate things"
    assert formatted[0]["parameters"] == {"type": "object"}
