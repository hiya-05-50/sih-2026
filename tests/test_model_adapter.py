"""Tests for Sprint 0 ModelAdapter contract and FixtureModelAdapter.

Covers:
    - adapter contract implementation (ABC conformance)
    - generate()
    - stream()
    - tool_call()
    - health_check()
    - capabilities()
    - fixture adapter determinism
    - fixture adapter capability reporting
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from app.adapters.base import ModelAdapter
from app.adapters.fixture import FixtureModelAdapter
from app.schemas.adapter import (
    GenerateRequest,
    GenerateResponse,
    HealthCheckResponse,
    StreamChunk,
    ToolCallRequest,
    ToolCallResponse,
)
from app.schemas.model_registry import ModelRegistryEntry
from shared.enums import ModelCapability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(**overrides) -> ModelRegistryEntry:
    """Build a minimal ModelRegistryEntry for test use."""
    base = {
        "model_id": "fixture-test-model",
        "name": "Fixture Test Model",
        "family": "fixture",
        "capabilities": [ModelCapability.TEXT, ModelCapability.REASONING],
        "context_length": 4096,
        "tool_calling": True,
    }
    base.update(overrides)
    return ModelRegistryEntry(**base)


def _make_adapter(**entry_overrides) -> FixtureModelAdapter:
    """Build a FixtureModelAdapter with sensible defaults."""
    return FixtureModelAdapter(registry_entry=_make_entry(**entry_overrides))


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)



async def _collect_stream(adapter: FixtureModelAdapter, request: GenerateRequest) -> list[StreamChunk]:
    """Collect all chunks from a stream() call."""
    chunks: list[StreamChunk] = []
    async for chunk in adapter.stream(request):
        chunks.append(chunk)
    return chunks


# ---------------------------------------------------------------------------
# Contract conformance
# ---------------------------------------------------------------------------

class TestAdapterContract:
    """FixtureModelAdapter must fully implement the ModelAdapter ABC."""

    def test_fixture_is_model_adapter_subclass(self):
        assert issubclass(FixtureModelAdapter, ModelAdapter)

    def test_fixture_instance_is_model_adapter(self):
        adapter = _make_adapter()
        assert isinstance(adapter, ModelAdapter)

    def test_cannot_instantiate_abstract_adapter(self):
        """The base ABC must not be directly instantiable."""
        with pytest.raises(TypeError):
            ModelAdapter()  # type: ignore[abstract]

    def test_incomplete_subclass_rejected(self):
        """A subclass missing required methods must fail to instantiate."""

        class Incomplete(ModelAdapter):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------

class TestGenerate:
    """Tests for the generate() adapter method."""

    def test_generate_returns_response(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        response = _run(adapter.generate(request))
        assert isinstance(response, GenerateResponse)

    def test_generate_returns_deterministic_text(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        r1 = _run(adapter.generate(request))
        r2 = _run(adapter.generate(request))
        assert r1.text == r2.text

    def test_generate_reports_correct_model_id(self):
        adapter = _make_adapter(model_id="custom-id")
        request = GenerateRequest(prompt="Hello")
        response = _run(adapter.generate(request))
        assert response.model_id == "custom-id"

    def test_generate_includes_usage(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello world")
        response = _run(adapter.generate(request))
        assert response.usage is not None
        assert "prompt_tokens" in response.usage
        assert "completion_tokens" in response.usage

    def test_generate_custom_response_text(self):
        entry = _make_entry()
        adapter = FixtureModelAdapter(registry_entry=entry, response_text="Custom!")
        request = GenerateRequest(prompt="Hello")
        response = _run(adapter.generate(request))
        assert response.text == "Custom!"


# ---------------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------------

class TestStream:
    """Tests for the stream() adapter method."""

    def test_stream_yields_chunks(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        chunks = _run(_collect_stream(adapter, request))
        assert len(chunks) > 0
        assert all(isinstance(c, StreamChunk) for c in chunks)

    def test_stream_last_chunk_is_finished(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        chunks = _run(_collect_stream(adapter, request))
        assert chunks[-1].finished is True

    def test_stream_intermediate_chunks_not_finished(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        chunks = _run(_collect_stream(adapter, request))
        for chunk in chunks[:-1]:
            assert chunk.finished is False

    def test_stream_is_deterministic(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        c1 = _run(_collect_stream(adapter, request))
        c2 = _run(_collect_stream(adapter, request))
        assert [c.text for c in c1] == [c.text for c in c2]

    def test_stream_concatenation_matches_expected(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Hello")
        chunks = _run(_collect_stream(adapter, request))
        full_text = "".join(c.text for c in chunks)
        assert full_text == "This is a deterministic fixture stream."


# ---------------------------------------------------------------------------
# tool_call()
# ---------------------------------------------------------------------------

class TestToolCall:
    """Tests for the tool_call() adapter method."""

    def test_tool_call_returns_response(self):
        adapter = _make_adapter()
        request = ToolCallRequest(
            prompt="Calculate 2+2",
            tools=[{"name": "calculator", "description": "Math tool"}],
        )
        response = _run(adapter.tool_call(request))
        assert isinstance(response, ToolCallResponse)

    def test_tool_call_selects_first_tool(self):
        adapter = _make_adapter()
        request = ToolCallRequest(
            prompt="Do something",
            tools=[
                {"name": "first_tool", "description": "Tool A"},
                {"name": "second_tool", "description": "Tool B"},
            ],
        )
        response = _run(adapter.tool_call(request))
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "first_tool"

    def test_tool_call_returns_deterministic_arguments(self):
        adapter = _make_adapter()
        request = ToolCallRequest(
            prompt="Do something",
            tools=[{"name": "my_tool", "description": "A tool"}],
        )
        r1 = _run(adapter.tool_call(request))
        r2 = _run(adapter.tool_call(request))
        assert r1.tool_calls[0].arguments == r2.tool_calls[0].arguments

    def test_tool_call_does_not_execute_tool(self):
        """The adapter returns a tool selection — it must NOT run the tool."""
        adapter = _make_adapter()
        request = ToolCallRequest(
            prompt="Delete everything",
            tools=[{"name": "dangerous_tool", "description": "DO NOT RUN"}],
        )
        response = _run(adapter.tool_call(request))
        # We only get a selection, never an execution result
        assert response.tool_calls[0].tool_name == "dangerous_tool"
        assert "result" in response.tool_calls[0].arguments

    def test_tool_call_reports_correct_model_id(self):
        adapter = _make_adapter(model_id="tool-model")
        request = ToolCallRequest(
            prompt="Hello",
            tools=[{"name": "t", "description": "d"}],
        )
        response = _run(adapter.tool_call(request))
        assert response.model_id == "tool-model"


# ---------------------------------------------------------------------------
# health_check()
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Tests for the health_check() adapter method."""

    def test_health_check_returns_response(self):
        adapter = _make_adapter()
        response = _run(adapter.health_check())
        assert isinstance(response, HealthCheckResponse)

    def test_health_check_is_healthy(self):
        adapter = _make_adapter()
        response = _run(adapter.health_check())
        assert response.healthy is True

    def test_health_check_reports_correct_model_id(self):
        adapter = _make_adapter(model_id="health-model")
        response = _run(adapter.health_check())
        assert response.model_id == "health-model"

    def test_health_check_includes_detail(self):
        adapter = _make_adapter()
        response = _run(adapter.health_check())
        assert response.detail is not None
        assert len(response.detail) > 0

    def test_health_check_is_deterministic(self):
        adapter = _make_adapter()
        r1 = _run(adapter.health_check())
        r2 = _run(adapter.health_check())
        assert r1.healthy == r2.healthy
        assert r1.model_id == r2.model_id
        assert r1.detail == r2.detail


# ---------------------------------------------------------------------------
# capabilities()
# ---------------------------------------------------------------------------

class TestCapabilities:
    """Tests for the capabilities() adapter method."""

    def test_capabilities_returns_list(self):
        adapter = _make_adapter()
        caps = adapter.capabilities()
        assert isinstance(caps, list)

    def test_capabilities_returns_model_capability_values(self):
        adapter = _make_adapter()
        caps = adapter.capabilities()
        for cap in caps:
            assert isinstance(cap, ModelCapability)

    def test_capabilities_matches_registry_entry(self):
        entry = _make_entry(capabilities=[
            ModelCapability.TEXT,
            ModelCapability.VISION,
            ModelCapability.CODING,
        ])
        adapter = FixtureModelAdapter(registry_entry=entry)
        caps = adapter.capabilities()
        assert caps == [ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODING]

    def test_capabilities_single_value(self):
        entry = _make_entry(capabilities=[ModelCapability.EMBEDDING])
        adapter = FixtureModelAdapter(registry_entry=entry)
        caps = adapter.capabilities()
        assert caps == [ModelCapability.EMBEDDING]

    def test_capabilities_all_values(self):
        all_caps = list(ModelCapability)
        entry = _make_entry(capabilities=all_caps)
        adapter = FixtureModelAdapter(registry_entry=entry)
        assert adapter.capabilities() == all_caps


# ---------------------------------------------------------------------------
# Fixture adapter determinism (cross-method)
# ---------------------------------------------------------------------------

class TestFixtureDeterminism:
    """The fixture adapter must be fully deterministic across calls."""

    def test_multiple_generates_same_result(self):
        adapter = _make_adapter()
        request = GenerateRequest(prompt="Determinism test")
        results = [_run(adapter.generate(request)).text for _ in range(5)]
        assert len(set(results)) == 1

    def test_multiple_tool_calls_same_result(self):
        adapter = _make_adapter()
        request = ToolCallRequest(
            prompt="Determinism test",
            tools=[{"name": "t", "description": "d"}],
        )
        results = [
            _run(adapter.tool_call(request)).tool_calls[0].arguments
            for _ in range(5)
        ]
        assert all(r == results[0] for r in results)

    def test_separate_adapter_instances_same_results(self):
        """Two adapters with the same config must produce identical output."""
        a1 = _make_adapter()
        a2 = _make_adapter()
        request = GenerateRequest(prompt="Instance test")
        assert _run(a1.generate(request)).text == _run(a2.generate(request)).text

    def test_capabilities_stable_across_calls(self):
        adapter = _make_adapter()
        c1 = adapter.capabilities()
        c2 = adapter.capabilities()
        assert c1 == c2
