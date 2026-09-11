"""Tests for the AdapterManager."""

import asyncio

import pytest

from app.adapters.base import ModelAdapter
from app.adapters.fixture import FixtureModelAdapter
from app.adapters.manager import AdapterManager
from app.schemas.model_registry import ModelRegistryEntry
from app.services.registry import ModelRegistry
from shared.enums import ModelCapability


def _make_entry(model_id: str = "mgr-model") -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id=model_id,
        name="Manager Test Model",
        family="test",
        capabilities=[ModelCapability.TEXT],
        context_length=4096,
        tool_calling=False,
    )


def _make_manager() -> tuple[ModelRegistry, AdapterManager]:
    reg = ModelRegistry()
    mgr = AdapterManager(reg)
    return reg, mgr


# ---------------------------------------------------------------------------
# Adapter creation
# ---------------------------------------------------------------------------


class TestGetAdapter:
    def test_returns_adapter_for_registered_model(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry())
        adapter = mgr.get_adapter("mgr-model")
        assert adapter is not None
        assert isinstance(adapter, ModelAdapter)

    def test_returns_fixture_adapter(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry())
        adapter = mgr.get_adapter("mgr-model")
        assert isinstance(adapter, FixtureModelAdapter)

    def test_returns_none_for_unknown_model(self):
        _reg, mgr = _make_manager()
        assert mgr.get_adapter("unknown") is None

    def test_caches_adapter_instance(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry())
        a1 = mgr.get_adapter("mgr-model")
        a2 = mgr.get_adapter("mgr-model")
        assert a1 is a2

    def test_different_models_get_different_adapters(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry(model_id="a"))
        reg.register(_make_entry(model_id="b"))
        assert mgr.get_adapter("a") is not mgr.get_adapter("b")


# ---------------------------------------------------------------------------
# Adapter removal
# ---------------------------------------------------------------------------


class TestRemoveAdapter:
    def test_remove_clears_cache(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry())
        mgr.get_adapter("mgr-model")  # populate cache
        mgr.remove_adapter("mgr-model")
        # Next call should create a new instance
        reg.register(_make_entry())  # re-register so lookup works
        a = mgr.get_adapter("mgr-model")
        assert a is not None

    def test_remove_nonexistent_is_safe(self):
        _reg, mgr = _make_manager()
        mgr.remove_adapter("no-such-model")  # should not raise


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


class TestHealthCheckAll:
    def test_empty_when_no_adapters(self):
        _reg, mgr = _make_manager()
        results = asyncio.run(
            mgr.health_check_all()
        )
        assert results == {}

    def test_returns_health_for_active_adapters(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry(model_id="m1"))
        reg.register(_make_entry(model_id="m2"))
        mgr.get_adapter("m1")
        mgr.get_adapter("m2")
        results = asyncio.run(
            mgr.health_check_all()
        )

        assert len(results) == 2
        assert results["m1"].healthy is True
        assert results["m2"].healthy is True

    def test_health_reports_correct_model_ids(self):
        reg, mgr = _make_manager()
        reg.register(_make_entry(model_id="mx"))
        mgr.get_adapter("mx")
        results = asyncio.run(
            mgr.health_check_all()
        )
        assert results["mx"].model_id == "mx"

