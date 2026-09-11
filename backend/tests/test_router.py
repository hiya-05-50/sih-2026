from __future__ import annotations

"""Tests for the 5-step ModelRouter pipeline.

Covers:
    - Capability filtering
    - Context-length filtering
    - Feasibility (VRAM) filtering
    - Composite scoring
    - Fallback behavior
    - Response shape and reasoning
"""

import pytest

from app.schemas.model_registry import BenchmarkProfile, ModelRegistryEntry
from app.schemas.routing import RouteRequest
from app.services.registry import ModelRegistry
from app.services.router import ModelRouter
from shared.enums import ModelCapability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    model_id: str = "r-model",
    name: str = "Router Model",
    capabilities: list | None = None,
    context_length: int = 4096,
    benchmark_profile: BenchmarkProfile | None = None,
    vram_footprint: float | None = None,
) -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id=model_id,
        name=name,
        family="test",
        capabilities=capabilities or [ModelCapability.TEXT],
        context_length=context_length,
        tool_calling=False,
        benchmark_profile=benchmark_profile,
        vram_footprint=vram_footprint,
    )


def _make_router() -> tuple[ModelRegistry, ModelRouter]:
    reg = ModelRegistry()
    rtr = ModelRouter(reg)
    return reg, rtr


# ---------------------------------------------------------------------------
# Step 1: Capability matching
# ---------------------------------------------------------------------------


class TestCapabilityMatch:
    def test_single_capability_match(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(capabilities=[ModelCapability.TEXT]))
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert result is not None
        assert result.model_id == "r-model"

    def test_multi_capability_match(self):
        reg, rtr = _make_router()
        reg.register(
            _make_entry(
                capabilities=[ModelCapability.TEXT, ModelCapability.CODING]
            )
        )
        result = rtr.route(
            RouteRequest(
                required_capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.CODING,
                ]
            )
        )
        assert result is not None

    def test_no_match_triggers_fallback(self):
        """When no model matches, fallback relaxes to TEXT-only."""
        reg, rtr = _make_router()
        reg.register(_make_entry(capabilities=[ModelCapability.TEXT]))
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.VISION])
        )
        # Fallback returns a TEXT model with fallback reasoning
        assert result is not None
        assert "fallback" in result.reasoning.lower()

    def test_empty_registry_returns_none(self):
        _reg, rtr = _make_router()
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert result is None

    def test_superset_capabilities_match(self):
        reg, rtr = _make_router()
        reg.register(
            _make_entry(
                capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.CODING,
                    ModelCapability.REASONING,
                ]
            )
        )
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert result is not None

    def test_subset_capabilities_triggers_fallback(self):
        """Model with TEXT only → fallback when VISION+TEXT required."""
        reg, rtr = _make_router()
        reg.register(_make_entry(capabilities=[ModelCapability.TEXT]))
        result = rtr.route(
            RouteRequest(
                required_capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.VISION,
                ]
            )
        )
        # Fallback to TEXT model
        assert result is not None
        assert "fallback" in result.reasoning.lower()


# ---------------------------------------------------------------------------
# Context length filtering
# ---------------------------------------------------------------------------


class TestContextLengthFilter:
    def test_meets_minimum(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(context_length=8192))
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                min_context_length=4096,
            )
        )
        assert result is not None

    def test_exact_minimum(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(context_length=4096))
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                min_context_length=4096,
            )
        )
        assert result is not None

    def test_below_minimum_triggers_fallback(self):
        """Model below context min → fallback (still TEXT capable)."""
        reg, rtr = _make_router()
        reg.register(_make_entry(context_length=2048))
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                min_context_length=4096,
            )
        )
        # Fallback returns the model since it's the only TEXT model
        assert result is not None
        assert "fallback" in result.reasoning.lower()


# ---------------------------------------------------------------------------
# Step 2: Feasibility (VRAM) filter
# ---------------------------------------------------------------------------


class TestFeasibilityFilter:
    def test_model_fits_in_vram(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(vram_footprint=4.0))  # 4 GB = 4096 MB
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                available_vram_mb=8192.0,  # 8 GB
            )
        )
        assert result is not None
        assert result.model_id == "r-model"

    def test_model_exceeds_vram_triggers_fallback(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(vram_footprint=10.0))  # 10 GB = 10240 MB
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                available_vram_mb=8192.0,  # 8 GB
            )
        )
        # Fallback triggered because the model exceeds VRAM
        assert result is not None
        assert "fallback" in result.reasoning.lower()

    def test_unknown_vram_assumed_feasible(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(vram_footprint=None))
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                available_vram_mb=4096.0,
            )
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Step 3: Composite scoring
# ---------------------------------------------------------------------------


class TestCompositeScoring:
    def test_prefers_lower_latency(self):
        reg, rtr = _make_router()
        reg.register(
            _make_entry(
                model_id="slow",
                name="Slow",
                benchmark_profile=BenchmarkProfile(latency_ms=200.0),
            )
        )
        reg.register(
            _make_entry(
                model_id="fast",
                name="Fast",
                benchmark_profile=BenchmarkProfile(latency_ms=50.0),
            )
        )
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                prefer_low_latency=True,
            )
        )
        assert result is not None
        assert result.model_id == "fast"

    def test_scoring_breakdown_in_candidates(self):
        reg, rtr = _make_router()
        reg.register(
            _make_entry(
                benchmark_profile=BenchmarkProfile(latency_ms=100.0),
                vram_footprint=4.0,
            )
        )
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert result is not None
        assert len(result.candidates) > 0
        candidate = result.candidates[0]
        assert candidate.score > 0
        assert candidate.latency_score >= 0
        assert candidate.vram_score >= 0
        assert candidate.capability_score >= 0

    def test_unmeasured_models_get_neutral_scores(self):
        reg, rtr = _make_router()
        reg.register(_make_entry())  # no benchmark, no vram
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert result is not None
        candidate = result.candidates[0]
        # Neutral score for unmeasured = 0.5
        assert candidate.latency_score == 0.5
        assert candidate.vram_score == 0.5


# ---------------------------------------------------------------------------
# Step 5: Fallback
# ---------------------------------------------------------------------------


class TestFallback:
    def test_fallback_includes_explanation(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(capabilities=[ModelCapability.TEXT]))
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.EMBEDDING])
        )
        assert result is not None
        assert "fallback" in result.reasoning.lower()
        assert "TEXT" in result.reasoning

    def test_empty_registry_no_fallback(self):
        _reg, rtr = _make_router()
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.VISION])
        )
        assert result is None


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


class TestRouteResponse:
    def test_response_contains_reasoning(self):
        reg, rtr = _make_router()
        reg.register(_make_entry())
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert result.reasoning
        assert "Router Model" in result.reasoning

    def test_response_includes_capabilities(self):
        reg, rtr = _make_router()
        reg.register(
            _make_entry(
                capabilities=[ModelCapability.TEXT, ModelCapability.CODING]
            )
        )
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert ModelCapability.TEXT in result.capabilities
        assert ModelCapability.CODING in result.capabilities

    def test_reasoning_mentions_all_pipeline_steps(self):
        reg, rtr = _make_router()
        reg.register(
            _make_entry(
                benchmark_profile=BenchmarkProfile(latency_ms=50.0),
            )
        )
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.TEXT])
        )
        assert "Step 1" in result.reasoning
        assert "Step 2" in result.reasoning
        assert "Step 3" in result.reasoning
        assert "Step 4" in result.reasoning

