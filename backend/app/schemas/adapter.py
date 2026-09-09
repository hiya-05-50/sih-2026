from __future__ import annotations

"""Sprint 0 – ModelAdapter request/response schemas.

Typed inputs and outputs for the ModelAdapter contract.
These Pydantic models define the data shapes that flow through
every adapter method, independent of the underlying inference runtime.
"""

import enum
import sys
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

# Polyfill enum.StrEnum for Python < 3.11 so that shared/enums.py
# (which uses `from enum import StrEnum`) can be imported unchanged.
if not hasattr(enum, "StrEnum"):
    class _StrEnum(str, enum.Enum):
        """Minimal StrEnum backport for Python 3.10."""
    enum.StrEnum = _StrEnum  # type: ignore[attr-defined]

# Ensure the repo root is importable so `shared.enums` resolves correctly.
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from shared.enums import ModelCapability


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    """Input for a non-streaming text generation call."""

    prompt: str = Field(..., description="The user prompt / instruction")
    system_prompt: Optional[str] = Field(
        None, description="Optional system-level instruction"
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None, gt=0, description="Maximum tokens to generate"
    )


class GenerateResponse(BaseModel):
    """Output of a non-streaming text generation call."""

    text: str = Field(..., description="Generated text")
    model_id: str = Field(..., description="ID of the model that produced the response")
    usage: Optional[dict[str, int]] = Field(
        None, description="Token usage statistics (prompt_tokens, completion_tokens)"
    )


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------

class StreamChunk(BaseModel):
    """A single chunk emitted during streaming generation."""

    text: str = Field(..., description="Incremental text fragment")
    finished: bool = Field(
        False, description="True if this is the final chunk"
    )


# ---------------------------------------------------------------------------
# Tool Call
# ---------------------------------------------------------------------------

class ToolCallRequest(BaseModel):
    """Input for a tool-calling invocation."""

    prompt: str = Field(..., description="User prompt that may require tool use")
    system_prompt: Optional[str] = Field(
        None, description="Optional system-level instruction"
    )
    tools: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="Tool definitions the model can choose from (JSON Schema format)",
    )
    temperature: float = Field(
        0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )


class ToolCallResult(BaseModel):
    """A single tool call selected by the model."""

    tool_name: str = Field(..., description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(
        ..., description="Arguments to pass to the tool"
    )


class ToolCallResponse(BaseModel):
    """Output of a tool-calling invocation."""

    tool_calls: list[ToolCallResult] = Field(
        ..., description="Tools selected by the model"
    )
    model_id: str = Field(..., description="ID of the model that produced the response")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class HealthCheckResponse(BaseModel):
    """Output of an adapter health check."""

    healthy: bool = Field(..., description="Whether the model backend is healthy")
    model_id: str = Field(..., description="ID of the model being checked")
    detail: Optional[str] = Field(
        None, description="Human-readable status detail"
    )
