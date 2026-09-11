import pytest
import asyncio
from app.services.agent.loop import AgentLoop
from app.services.tools.registry import ToolRegistry
from shared.enums import TaskState

class MockAdapter:
    """A mock adapter that always decides to call a tool, creating an infinite loop."""
    async def tool_call(self, request):
        from app.schemas.adapter import ToolCallResponse, ToolCallResult
        # Always call 'calculate' tool to force a loop
        return ToolCallResponse(
            model_id="mock",
            tool_calls=[ToolCallResult(tool_name="calculate", arguments={"expression": "1+1"})]
        )

def test_agent_loop_max_steps():
    """Test that the agent loop halts when MAX_AGENT_STEPS is exceeded."""
    registry = ToolRegistry()
    from app.services.tools.implementations import register_all_tools
    register_all_tools(registry)
    
    adapter = MockAdapter()
    loop = AgentLoop(task_id="test-task", adapter=adapter, registry=registry)
    
    # Restrict steps to a very small number for the test
    loop.state.bounds.max_agent_steps = 3
    
    # Run loop
    state = asyncio.run(loop.run())
    
    # It should have failed due to max_agent_steps
    assert state.current_state == TaskState.FAILED
    assert "max_agent_steps" in state.error_message
    assert state.step_count == 3
