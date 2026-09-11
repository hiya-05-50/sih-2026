"""Tests for the Sprint 0 Model Registry schema.

Covers:
    - Valid model registry entry construction
    - Multiple capabilities
    - Optional/null benchmark fields
    - Rejection of invalid capability values
"""

import pytest
from pydantic import ValidationError

from app.schemas.model_registry import BenchmarkProfile, ModelRegistryEntry
from shared.enums import ModelCapability


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_entry(**overrides) -> dict:
    """Return the smallest valid ModelRegistryEntry dict, with overrides."""
    base = {
        "model_id": "llama-3.1-8b",
        "name": "Llama 3.1 8B",
        "family": "llama",
        "capabilities": [ModelCapability.TEXT],
        "context_length": 8192,
        "tool_calling": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid entry
# ---------------------------------------------------------------------------

class TestValidEntry:
    """A well-formed registry entry should round-trip cleanly."""

    def test_minimal_valid_entry(self):
        entry = ModelRegistryEntry(**_minimal_entry())
        assert entry.model_id == "llama-3.1-8b"
        assert entry.name == "Llama 3.1 8B"
        assert entry.family == "llama"
        assert entry.capabilities == [ModelCapability.TEXT]
        assert entry.context_length == 8192
        assert entry.tool_calling is False

    def test_full_entry_with_all_fields(self):
        entry = ModelRegistryEntry(**_minimal_entry(
            vram_footprint=6.5,
            quantization="Q4_K_M",
            license="Apache-2.0",
            benchmark_profile={
                "accuracy": 0.87,
                "latency_ms": 42.5,
                "throughput_tps": 120.0,
                "memory_mb": 6500.0,
                "notes": "Tested on A100",
            },
        ))
        assert entry.vram_footprint == 6.5
        assert entry.quantization == "Q4_K_M"
        assert entry.license == "Apache-2.0"
        assert entry.benchmark_profile is not None
        assert entry.benchmark_profile.accuracy == 0.87


# ---------------------------------------------------------------------------
# Multiple capabilities
# ---------------------------------------------------------------------------

class TestMultipleCapabilities:
    """The capabilities field must accept more than one value."""

    def test_multiple_capabilities(self):
        caps = [
            ModelCapability.TEXT,
            ModelCapability.VISION,
            ModelCapability.REASONING,
            ModelCapability.TOOL_CALLING,
        ]
        entry = ModelRegistryEntry(**_minimal_entry(capabilities=caps))
        assert len(entry.capabilities) == 4
        assert ModelCapability.VISION in entry.capabilities
        assert ModelCapability.TOOL_CALLING in entry.capabilities

    def test_all_capabilities(self):
        all_caps = list(ModelCapability)
        entry = ModelRegistryEntry(**_minimal_entry(capabilities=all_caps))
        assert len(entry.capabilities) == len(ModelCapability)


# ---------------------------------------------------------------------------
# Optional / null benchmark fields
# ---------------------------------------------------------------------------

class TestOptionalBenchmarkFields:
    """Benchmark-related and runtime fields must accept None."""

    def test_benchmark_profile_defaults_to_none(self):
        entry = ModelRegistryEntry(**_minimal_entry())
        assert entry.benchmark_profile is None

    def test_vram_footprint_defaults_to_none(self):
        entry = ModelRegistryEntry(**_minimal_entry())
        assert entry.vram_footprint is None

    def test_quantization_defaults_to_none(self):
        entry = ModelRegistryEntry(**_minimal_entry())
        assert entry.quantization is None

    def test_license_defaults_to_none(self):
        entry = ModelRegistryEntry(**_minimal_entry())
        assert entry.license is None

    def test_partial_benchmark_profile(self):
        entry = ModelRegistryEntry(**_minimal_entry(
            benchmark_profile={"accuracy": 0.92}
        ))
        assert entry.benchmark_profile.accuracy == 0.92
        assert entry.benchmark_profile.latency_ms is None
        assert entry.benchmark_profile.throughput_tps is None
        assert entry.benchmark_profile.memory_mb is None
        assert entry.benchmark_profile.notes is None

    def test_empty_benchmark_profile(self):
        entry = ModelRegistryEntry(**_minimal_entry(
            benchmark_profile={}
        ))
        assert entry.benchmark_profile is not None
        assert entry.benchmark_profile.accuracy is None


# ---------------------------------------------------------------------------
# Rejection of invalid values
# ---------------------------------------------------------------------------

class TestInvalidValues:
    """The schema must reject data that violates the contract."""

    def test_invalid_capability_value_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ModelRegistryEntry(**_minimal_entry(
                capabilities=["NOT_A_REAL_CAPABILITY"]
            ))
        assert "capabilities" in str(exc_info.value)

    def test_empty_capabilities_rejected(self):
        with pytest.raises(ValidationError):
            ModelRegistryEntry(**_minimal_entry(capabilities=[]))

    def test_missing_required_field_rejected(self):
        data = _minimal_entry()
        del data["model_id"]
        with pytest.raises(ValidationError):
            ModelRegistryEntry(**data)

    def test_zero_context_length_rejected(self):
        with pytest.raises(ValidationError):
            ModelRegistryEntry(**_minimal_entry(context_length=0))

    def test_negative_context_length_rejected(self):
        with pytest.raises(ValidationError):
            ModelRegistryEntry(**_minimal_entry(context_length=-1))

    def test_mixed_valid_and_invalid_capabilities_rejected(self):
        with pytest.raises(ValidationError):
            ModelRegistryEntry(**_minimal_entry(
                capabilities=[ModelCapability.TEXT, "INVALID"]
            ))
