from __future__ import annotations

"""Sprint 0 – FixtureModelAdapter.

A deterministic, no-network adapter for testing and integration work.
Every response is predictable and locally computed — no external
service is ever contacted.
"""

from typing import AsyncIterator, Optional

from app.adapters.base import ModelAdapter
from app.schemas.adapter import (
    GenerateRequest,
    GenerateResponse,
    HealthCheckResponse,
    StreamChunk,
    ToolCallRequest,
    ToolCallResponse,
    ToolCallResult,
)
from app.schemas.model_registry import ModelRegistryEntry
from shared.enums import ModelCapability


# Deterministic fixture constants
_FIXTURE_RESPONSE_TEXT = "This is a deterministic fixture response."
_FIXTURE_STREAM_CHUNKS = [
    "This is ",
    "a deterministic ",
    "fixture stream.",
]
_FIXTURE_TOOL_NAME = "fixture_tool"
_FIXTURE_TOOL_ARGS = {"result": "deterministic_fixture_value"}


class FixtureModelAdapter(ModelAdapter):
    """Deterministic model adapter for tests and local integration.

    - Never contacts an external service.
    - Every method returns a predictable, hard-coded response.
    - Configurable via a ``ModelRegistryEntry`` so that tests can
      control the model_id and capabilities reported.

    Args:
        registry_entry: Model metadata that configures this adapter's
            identity and reported capabilities.
        response_text: Optional override for the generate() response text.
    """

    def __init__(
        self,
        registry_entry: ModelRegistryEntry,
        *,
        response_text: Optional[str] = None,
    ) -> None:
        self._entry = registry_entry
        self._response_text = response_text or _FIXTURE_RESPONSE_TEXT

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model_id(self) -> str:
        """The model_id from the underlying registry entry."""
        return self._entry.model_id

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Return a deterministic text response."""
        return GenerateResponse(
            text=self._response_text,
            model_id=self.model_id,
            usage={"prompt_tokens": len(request.prompt.split()),
                    "completion_tokens": len(self._response_text.split())},
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Yield deterministic text chunks."""
        for i, chunk_text in enumerate(_FIXTURE_STREAM_CHUNKS):
            is_last = i == len(_FIXTURE_STREAM_CHUNKS) - 1
            yield StreamChunk(text=chunk_text, finished=is_last)

    # ------------------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------------------

    async def tool_call(self, request: ToolCallRequest) -> ToolCallResponse:
        """Return a deterministic tool-call selection.

        Always selects the first tool provided in the request and
        returns fixed arguments.  Does NOT execute any tool.
        """
        selected_tool_name = request.tools[0].get("name", _FIXTURE_TOOL_NAME)
        return ToolCallResponse(
            tool_calls=[
                ToolCallResult(
                    tool_name=selected_tool_name,
                    arguments=_FIXTURE_TOOL_ARGS,
                ),
            ],
            model_id=self.model_id,
        )

    # ------------------------------------------------------------------
    # Operational
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthCheckResponse:
        """Always report healthy — no external dependencies."""
        return HealthCheckResponse(
            healthy=True,
            model_id=self.model_id,
            detail="Fixture adapter is always healthy",
        )

    def capabilities(self) -> list[ModelCapability]:
        """Return capabilities from the configured registry entry."""
        return list(self._entry.capabilities)
