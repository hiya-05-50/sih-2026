from __future__ import annotations

"""Tests for the ModelRouter."""

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
) -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id=model_id,
        name=name,
        family="test",
        capabilities=capabilities or [ModelCapability.TEXT],
        context_length=context_length,
        tool_calling=False,
        benchmark_profile=benchmark_profile,
    )


def _make_router() -> tuple[ModelRegistry, ModelRouter]:
    reg = ModelRegistry()
    rtr = ModelRouter(reg)
    return reg, rtr


# ---------------------------------------------------------------------------
# Capability matching
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

    def test_no_match_returns_none(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(capabilities=[ModelCapability.TEXT]))
        result = rtr.route(
            RouteRequest(required_capabilities=[ModelCapability.VISION])
        )
        assert result is None

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

    def test_subset_capabilities_no_match(self):
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
        assert result is None


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

    def test_below_minimum_excluded(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(context_length=2048))
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                min_context_length=4096,
            )
        )
        assert result is None


# ---------------------------------------------------------------------------
# Benchmark-based ranking
# ---------------------------------------------------------------------------


class TestBenchmarkRanking:
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

    def test_models_without_profile_ranked_last(self):
        reg, rtr = _make_router()
        reg.register(_make_entry(model_id="no-bench", name="No Bench"))
        reg.register(
            _make_entry(
                model_id="benched",
                name="Benched",
                benchmark_profile=BenchmarkProfile(latency_ms=100.0),
            )
        )
        result = rtr.route(
            RouteRequest(
                required_capabilities=[ModelCapability.TEXT],
                prefer_low_latency=True,
            )
        )
        assert result.model_id == "benched"


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
