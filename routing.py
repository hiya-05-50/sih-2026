"""SAFIRE routing request/response schemas.

Typed inputs and outputs for the model routing API.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from shared.enums import ModelCapability


class RouteRequest(BaseModel):
    """Input for a model routing request."""

    required_capabilities: list[ModelCapability] = Field(
        ...,
        min_length=1,
        description="Capabilities the target model must support",
    )
    min_context_length: Optional[int] = Field(
        None,
        gt=0,
        description="Minimum context length in tokens the model must support",
    )
    prefer_low_latency: bool = Field(
        False,
        description="When True, prefer models with lower latency benchmarks",
    )


class RouteResponse(BaseModel):
    """Output of a model routing request."""

    model_id: str = Field(..., description="ID of the selected model")
    model_name: str = Field(..., description="Human-readable name of the selected model")
    capabilities: list[ModelCapability] = Field(
        ..., description="Capabilities of the selected model"
    )
    reasoning: str = Field(
        ..., description="Human-readable explanation of why this model was selected"
    )
