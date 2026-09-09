from __future__ import annotations

"""Sprint 0 – Model Registry schema.

Defines the Pydantic model for a registered SAFIRE model entry.
Capabilities reference the canonical ModelCapability enum from shared/enums.py.
Benchmark and runtime fields are nullable; actual measurements are collected
during Sprint 1.
"""

import enum
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# Polyfill enum.StrEnum for Python < 3.11 so that shared/enums.py
# (which uses `from enum import StrEnum`) can be imported unchanged.
if not hasattr(enum, "StrEnum"):
    class _StrEnum(str, enum.Enum):
        """Minimal StrEnum backport for Python 3.10."""
    enum.StrEnum = _StrEnum  # type: ignore[attr-defined]

# Ensure the repo root is importable so `shared.enums` resolves correctly
# regardless of how the backend is launched.
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from shared.enums import ModelCapability


class BenchmarkProfile(BaseModel):
    """Structured placeholder for benchmark results.

    All fields are optional because actual measurements are collected
    during Sprint 1 model-benchmarking work.
    """

    accuracy: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Accuracy score (0-1) from benchmark evaluation"
    )
    latency_ms: Optional[float] = Field(
        None, ge=0.0, description="Mean latency in milliseconds per request"
    )
    throughput_tps: Optional[float] = Field(
        None, ge=0.0, description="Throughput in tokens per second"
    )
    memory_mb: Optional[float] = Field(
        None, ge=0.0, description="Peak memory usage in megabytes during benchmark"
    )
    notes: Optional[str] = Field(
        None, description="Free-form notes about the benchmark run"
    )


class ModelRegistryEntry(BaseModel):
    """Schema for a single model in the SAFIRE Model Registry.

    This is the Sprint 0 contract-freeze artifact that defines what
    information is tracked per registered model.
    """

    model_id: str = Field(
        ..., description="Unique identifier for the model"
    )
    name: str = Field(
        ..., description="Human-readable model name"
    )
    family: str = Field(
        ..., description="Model family (e.g. 'llama', 'mistral', 'gemma')"
    )
    capabilities: list[ModelCapability] = Field(
        ...,
        min_length=1,
        description="Capabilities this model supports; uses canonical ModelCapability enum",
    )
    context_length: int = Field(
        ..., gt=0, description="Maximum context length in tokens"
    )
    vram_footprint: Optional[float] = Field(
        None,
        description="Estimated VRAM footprint in GB (nullable until measured in Sprint 1)",
    )
    quantization: Optional[str] = Field(
        None,
        description="Quantization level (e.g. 'Q4_K_M', 'Q8_0', 'FP16', None for full precision)",
    )
    tool_calling: bool = Field(
        ..., description="Whether the model supports tool/function calling"
    )
    license: Optional[str] = Field(
        None, description="SPDX license identifier or license name"
    )
    benchmark_profile: Optional[BenchmarkProfile] = Field(
        None,
        description="Benchmark measurements; null until Sprint 1 benchmarking is run",
    )
