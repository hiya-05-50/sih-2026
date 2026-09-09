from __future__ import annotations

"""Sprint 0 – ModelAdapter abstract base class.

Defines the runtime-agnostic contract that every model adapter
(Ollama, vLLM, fixture, etc.) must implement.  Concrete adapters
are introduced in later sprints; this module only defines the interface.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.schemas.adapter import (
    GenerateRequest,
    GenerateResponse,
    HealthCheckResponse,
    StreamChunk,
    ToolCallRequest,
    ToolCallResponse,
)
from shared.enums import ModelCapability


class ModelAdapter(ABC):
    """Abstract contract for a SAFIRE model adapter.

    Each adapter wraps a single model and exposes a uniform interface
    regardless of the underlying inference runtime.
    """

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate a complete text response (non-streaming).

        Args:
            request: The generation request containing prompt, temperature, etc.

        Returns:
            A GenerateResponse with the full generated text.
        """

    @abstractmethod
    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Generate a streaming text response, yielding chunks.

        Args:
            request: The generation request containing prompt, temperature, etc.

        Yields:
            StreamChunk instances; the last chunk has ``finished=True``.
        """

    # ------------------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------------------

    @abstractmethod
    async def tool_call(self, request: ToolCallRequest) -> ToolCallResponse:
        """Ask the model to select and parameterise one or more tools.

        The adapter must NOT execute the tools; it only returns the
        model's tool-call decisions.

        Args:
            request: The tool-call request with prompt and tool definitions.

        Returns:
            A ToolCallResponse listing the selected tools and arguments.
        """

    # ------------------------------------------------------------------
    # Operational
    # ------------------------------------------------------------------

    @abstractmethod
    async def health_check(self) -> HealthCheckResponse:
        """Check whether the underlying model backend is healthy.

        Returns:
            A HealthCheckResponse indicating health status.
        """

    @abstractmethod
    def capabilities(self) -> list[ModelCapability]:
        """Return the capabilities of the model this adapter wraps.

        Returns:
            A list of ModelCapability enum values.
        """
