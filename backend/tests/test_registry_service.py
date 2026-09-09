from __future__ import annotations

"""Tests for the in-memory ModelRegistry service."""

import pytest

from app.schemas.model_registry import ModelRegistryEntry
from app.services.registry import ModelRegistry
from shared.enums import ModelCapability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    model_id: str = "test-model",
    name: str = "Test Model",
    family: str = "test",
    capabilities: list | None = None,
    context_length: int = 4096,
    tool_calling: bool = False,
) -> ModelRegistryEntry:
    return ModelRegistryEntry(
        model_id=model_id,
        name=name,
        family=family,
        capabilities=capabilities or [ModelCapability.TEXT],
        context_length=context_length,
        tool_calling=tool_calling,
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestRegister:
    def test_register_returns_entry(self):
        reg = ModelRegistry()
        entry = _make_entry()
        result = reg.register(entry)
        assert result.model_id == "test-model"

    def test_register_stores_entry(self):
        reg = ModelRegistry()
        entry = _make_entry()
        reg.register(entry)
        assert reg.get("test-model") is not None

    def test_register_overwrites_existing(self):
        reg = ModelRegistry()
        reg.register(_make_entry(name="Original"))
        reg.register(_make_entry(name="Updated"))
        assert reg.get("test-model").name == "Updated"
        assert len(reg.list_all()) == 1


class TestGet:
    def test_get_existing(self):
        reg = ModelRegistry()
        reg.register(_make_entry())
        entry = reg.get("test-model")
        assert entry is not None
        assert entry.model_id == "test-model"

    def test_get_nonexistent_returns_none(self):
        reg = ModelRegistry()
        assert reg.get("no-such-model") is None


class TestListAll:
    def test_empty_registry(self):
        reg = ModelRegistry()
        assert reg.list_all() == []

    def test_lists_all_entries(self):
        reg = ModelRegistry()
        reg.register(_make_entry(model_id="a"))
        reg.register(_make_entry(model_id="b"))
        ids = {e.model_id for e in reg.list_all()}
        assert ids == {"a", "b"}


class TestDelete:
    def test_delete_existing(self):
        reg = ModelRegistry()
        reg.register(_make_entry())
        assert reg.delete("test-model") is True
        assert reg.get("test-model") is None

    def test_delete_nonexistent_returns_false(self):
        reg = ModelRegistry()
        assert reg.delete("no-such-model") is False

    def test_delete_does_not_affect_others(self):
        reg = ModelRegistry()
        reg.register(_make_entry(model_id="keep"))
        reg.register(_make_entry(model_id="remove"))
        reg.delete("remove")
        assert reg.get("keep") is not None
        assert len(reg.list_all()) == 1


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


class TestFindByCapability:
    def test_finds_matching_entries(self):
        reg = ModelRegistry()
        reg.register(_make_entry(model_id="text-model", capabilities=[ModelCapability.TEXT]))
        reg.register(_make_entry(model_id="vision-model", capabilities=[ModelCapability.VISION]))
        results = reg.find_by_capability(ModelCapability.TEXT)
        assert len(results) == 1
        assert results[0].model_id == "text-model"

    def test_returns_empty_when_no_match(self):
        reg = ModelRegistry()
        reg.register(_make_entry(capabilities=[ModelCapability.TEXT]))
        results = reg.find_by_capability(ModelCapability.EMBEDDING)
        assert results == []

    def test_finds_models_with_multiple_capabilities(self):
        reg = ModelRegistry()
        reg.register(
            _make_entry(
                model_id="multi",
                capabilities=[ModelCapability.TEXT, ModelCapability.CODING],
            )
        )
        assert len(reg.find_by_capability(ModelCapability.TEXT)) == 1
        assert len(reg.find_by_capability(ModelCapability.CODING)) == 1

    def test_empty_registry(self):
        reg = ModelRegistry()
        assert reg.find_by_capability(ModelCapability.TEXT) == []
