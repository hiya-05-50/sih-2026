from __future__ import annotations

"""Sprint 1 – Ollama Model Adapter.

Concrete adapter that communicates with a locally running Ollama instance
for real model inference.  Implements the full ModelAdapter ABC contract.
"""

import json
import logging
from typing import AsyncIterator, Optional

import httpx

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

logger = logging.getLogger(__name__)

# Default Ollama endpoint
_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT = 120.0  # seconds – model loading can be slow


class OllamaModelAdapter(ModelAdapter):
    """Adapter wrapping a single model served by Ollama.

    Uses Ollama's REST API:
    - ``POST /api/generate`` for text generation (streaming + non-streaming)
    - ``POST /api/chat``     for tool-calling via chat completions
    - ``GET  /api/tags``     for health checking (model availability)
    - ``GET  /api/ps``       for checking loaded models / VRAM usage

    Args:
        registry_entry: Model metadata including the ``ollama_model`` tag.
        base_url: Ollama API base URL (default: http://localhost:11434).
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        registry_entry: ModelRegistryEntry,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._entry = registry_entry
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._ollama_model = registry_entry.ollama_model or registry_entry.name

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
        """Non-streaming text generation via Ollama."""
        payload: dict = {
            "model": self._ollama_model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        response_text = data.get("response", "")
        # Ollama returns token counts in eval_count / prompt_eval_count
        usage = {}
        if "prompt_eval_count" in data:
            usage["prompt_tokens"] = data["prompt_eval_count"]
        if "eval_count" in data:
            usage["completion_tokens"] = data["eval_count"]

        return GenerateResponse(
            text=response_text,
            model_id=self.model_id,
            usage=usage or None,
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Streaming text generation via Ollama."""
        payload: dict = {
            "model": self._ollama_model,
            "prompt": request.prompt,
            "stream": True,
            "options": {
                "temperature": request.temperature,
            },
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk_data = json.loads(line)
                    text = chunk_data.get("response", "")
                    done = chunk_data.get("done", False)
                    yield StreamChunk(text=text, finished=done)

    # ------------------------------------------------------------------
    # Tool calling
    # ------------------------------------------------------------------

    async def tool_call(self, request: ToolCallRequest) -> ToolCallResponse:
        """Tool-call selection via Ollama's chat API.

        Uses the ``/api/chat`` endpoint with ``tools`` parameter.
        The adapter does NOT execute tools – it returns the model's
        tool-call decisions only.
        """
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Convert tool defs to Ollama format
        tools = []
        for tool_def in request.tools:
            tool_spec = {
                "type": "function",
                "function": {
                    "name": tool_def.get("name", "unknown"),
                    "description": tool_def.get("description", ""),
                    "parameters": tool_def.get("parameters", {
                        "type": "object",
                        "properties": {},
                    }),
                },
            }
            tools.append(tool_spec)

        payload = {
            "model": self._ollama_model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Parse tool calls from the response
        tool_calls_data = (
            data.get("message", {}).get("tool_calls", [])
        )

        results = []
        for tc in tool_calls_data:
            fn = tc.get("function", {})
            results.append(ToolCallResult(
                tool_name=fn.get("name", "unknown"),
                arguments=fn.get("arguments", {}),
            ))

        # If no tool calls returned, create a fallback indicating
        # the model chose not to call tools (return the text response)
        if not results:
            content = data.get("message", {}).get("content", "")
            results.append(ToolCallResult(
                tool_name=request.tools[0].get("name", "fallback"),
                arguments={"model_response": content or "No tool call made"},
            ))

        return ToolCallResponse(
            tool_calls=results,
            model_id=self.model_id,
        )

    # ------------------------------------------------------------------
    # Operational
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthCheckResponse:
        """Check whether the Ollama model is available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()

            # Check if our model is in the list
            available_models = [
                m.get("name", "") for m in data.get("models", [])
            ]
            # Ollama tags may include :latest or version suffixes
            model_found = any(
                self._ollama_model in m or m.startswith(self._ollama_model.split(":")[0])
                for m in available_models
            )

            if model_found:
                return HealthCheckResponse(
                    healthy=True,
                    model_id=self.model_id,
                    detail=f"Ollama model '{self._ollama_model}' is available",
                )
            else:
                return HealthCheckResponse(
                    healthy=False,
                    model_id=self.model_id,
                    detail=(
                        f"Model '{self._ollama_model}' not found in Ollama. "
                        f"Available: {', '.join(available_models) or 'none'}"
                    ),
                )
        except Exception as exc:
            return HealthCheckResponse(
                healthy=False,
                model_id=self.model_id,
                detail=f"Ollama unreachable: {exc}",
            )

    def capabilities(self) -> list[ModelCapability]:
        """Return capabilities from the configured registry entry."""
        return list(self._entry.capabilities)

    # ------------------------------------------------------------------
    # Ollama-specific helpers
    # ------------------------------------------------------------------

    async def get_running_models(self) -> list[dict]:
        """Query Ollama for currently loaded models and VRAM usage."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/ps")
                resp.raise_for_status()
                return resp.json().get("models", [])
        except Exception:
            return []
