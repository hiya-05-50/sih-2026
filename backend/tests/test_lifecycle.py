"""Tests for the Task Lifecycle Manager.

Covers:
    - Full lifecycle: INTAKE → CLASSIFY → PLAN → DELIVER
    - Task type classification to capabilities
    - State transition audit trail
    - Unknown task type handling
    - Error handling → FAILED state
"""

from __future__ import annotations

import asyncio

import pytest

from app.adapters.manager import AdapterManager
from app.schemas.model_registry import ModelRegistryEntry
from app.schemas.task import TASK_TYPE_CAPABILITIES, TaskProfile
from app.services.lifecycle import TaskLifecycleManager
from app.services.registry import ModelRegistry
from app.services.router import ModelRouter
from shared.enums import ModelCapability, TaskState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_pipeline(
    models: list[ModelRegistryEntry] | None = None,
) -> TaskLifecycleManager:
    """Build a lifecycle manager with fixture models."""
    reg = ModelRegistry()
    for m in (models or []):
        reg.register(m)
    router = ModelRouter(reg)
    mgr = AdapterManager(reg)
    return TaskLifecycleManager(reg, router, mgr)


def _reasoning_model() -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id="test-reasoning",
        name="Test Reasoning Model",
        family="test",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.REASONING,
            ModelCapability.CODING,
        ],
        context_length=8192,
        tool_calling=True,
        runtime="fixture",
    )


def _vision_model() -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id="test-vision",
        name="Test Vision Model",
        family="test",
        capabilities=[
            ModelCapability.TEXT,
            ModelCapability.VISION,
            ModelCapability.DOCUMENT_UNDERSTANDING,
        ],
        context_length=4096,
        tool_calling=False,
        runtime="fixture",
    )


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_full_lifecycle_success(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="code_review",
            description="Review this Python code for bugs",
        )
        result = _run(lm.execute(profile))
        assert result.current_state == TaskState.DELIVER
        assert result.error is None
        assert result.model_response is not None
        assert result.completed_at is not None

    def test_state_history_recorded(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="reasoning",
            description="Explain quantum computing",
        )
        result = _run(lm.execute(profile))
        # Should have transitions: INTAKE→CLASSIFY, CLASSIFY→PLAN, PLAN→DELIVER
        states = [t.to_state for t in result.state_history]
        assert TaskState.CLASSIFY in states
        assert TaskState.PLAN in states
        assert TaskState.DELIVER in states

    def test_routing_rationale_populated(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="code_review",
            description="Check for security issues",
        )
        result = _run(lm.execute(profile))
        assert result.routing_rationale is not None
        assert len(result.routing_rationale) > 0
        assert result.selected_model_name is not None


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    def test_code_review_maps_to_coding_caps(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="code_review",
            description="Review code",
        )
        result = _run(lm.execute(profile))
        assert ModelCapability.CODING in result.required_capabilities
        assert ModelCapability.REASONING in result.required_capabilities

    def test_document_analysis_maps_to_vision_caps(self):
        lm = _make_pipeline([_vision_model()])
        profile = TaskProfile(
            task_type="document_analysis",
            description="Analyze this report",
        )
        result = _run(lm.execute(profile))
        assert ModelCapability.VISION in result.required_capabilities

    def test_unknown_type_falls_back_to_text(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="unknown_task",
            description="Do something",
        )
        result = _run(lm.execute(profile))
        assert ModelCapability.TEXT in result.required_capabilities

    def test_custom_capabilities_override(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="code_review",
            description="Custom caps",
            required_capabilities=[ModelCapability.TEXT],
        )
        result = _run(lm.execute(profile))
        assert result.required_capabilities == [ModelCapability.TEXT]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_no_model_available(self):
        lm = _make_pipeline([])  # empty registry
        profile = TaskProfile(
            task_type="code_review",
            description="No models",
        )
        result = _run(lm.execute(profile))
        assert result.current_state == TaskState.FAILED
        assert result.error is not None


# ---------------------------------------------------------------------------
# Task store
# ---------------------------------------------------------------------------


class TestTaskStore:
    def test_get_task_after_execution(self):
        lm = _make_pipeline([_reasoning_model()])
        profile = TaskProfile(
            task_type="reasoning",
            description="Test",
        )
        result = _run(lm.execute(profile))
        retrieved = lm.get_task(result.task_id)
        assert retrieved is not None
        assert retrieved.task_id == result.task_id

    def test_list_tasks(self):
        lm = _make_pipeline([_reasoning_model()])
        _run(lm.execute(TaskProfile(task_type="reasoning", description="A")))
        _run(lm.execute(TaskProfile(task_type="reasoning", description="B")))
        assert len(lm.list_tasks()) == 2

    def test_get_nonexistent_task(self):
        lm = _make_pipeline([_reasoning_model()])
        assert lm.get_task("nonexistent") is None
