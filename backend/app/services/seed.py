from __future__ import annotations

"""Sprint 1 – Model Seed Service.

Auto-registers models from Ollama at startup.  Falls back to
fixture models when Ollama is not available, ensuring the system
always has models to work with.
"""

import logging
from typing import Optional

import httpx

from app.schemas.model_registry import ModelRegistryEntry
from app.services.registry import ModelRegistry
from shared.enums import ModelCapability

logger = logging.getLogger(__name__)

_OLLAMA_BASE_URL = "http://localhost:11434"

# Canonical model role definitions.
# Maps Ollama model tags to their SAFIRE capabilities and metadata.
MODEL_ROLES: dict[str, dict] = {
    "qwen2.5:7b": {
        "model_id": "qwen2.5-7b",
        "name": "Qwen 2.5 7B (Reasoning)",
        "family": "qwen",
        "capabilities": [
            ModelCapability.TEXT,
            ModelCapability.REASONING,
            ModelCapability.CODING,
            ModelCapability.TOOL_CALLING,
            ModelCapability.STRUCTURED_OUTPUT,
        ],
        "context_length": 32768,
        "tool_calling": True,
        "quantization": "Q4_K_M",
        "vram_footprint": 4.7,
        "license": "Apache-2.0",
    },
    "qwen2.5-coder:7b": {
        "model_id": "qwen2.5-coder-7b",
        "name": "Qwen 2.5 Coder 7B",
        "family": "qwen",
        "capabilities": [
            ModelCapability.TEXT,
            ModelCapability.CODING,
            ModelCapability.TOOL_CALLING,
            ModelCapability.STRUCTURED_OUTPUT,
        ],
        "context_length": 32768,
        "tool_calling": True,
        "quantization": "Q4_K_M",
        "vram_footprint": 4.7,
        "license": "Apache-2.0",
    },
    "llava:7b": {
        "model_id": "llava-7b",
        "name": "LLaVA 7B (Vision)",
        "family": "llava",
        "capabilities": [
            ModelCapability.TEXT,
            ModelCapability.VISION,
            ModelCapability.DOCUMENT_UNDERSTANDING,
        ],
        "context_length": 4096,
        "tool_calling": False,
        "quantization": "Q4_K_M",
        "vram_footprint": 4.7,
        "license": "Apache-2.0",
    },
}

# Fixture fallback models — always available, no Ollama required
FIXTURE_MODELS: list[dict] = [
    {
        "model_id": "fixture-reasoning",
        "name": "Fixture Reasoning Model",
        "family": "fixture",
        "capabilities": [
            ModelCapability.TEXT,
            ModelCapability.REASONING,
            ModelCapability.CODING,
        ],
        "context_length": 8192,
        "tool_calling": True,
        "runtime": "fixture",
    },
    {
        "model_id": "fixture-vision",
        "name": "Fixture Vision Model",
        "family": "fixture",
        "capabilities": [
            ModelCapability.TEXT,
            ModelCapability.VISION,
            ModelCapability.DOCUMENT_UNDERSTANDING,
        ],
        "context_length": 4096,
        "tool_calling": False,
        "runtime": "fixture",
    },
]


async def seed_models(registry: ModelRegistry) -> int:
    """Seed the registry with models from Ollama or fixtures.

    Queries Ollama for available models and registers those that
    have known role definitions.  Falls back to fixture models
    if Ollama is unreachable.

    Args:
        registry: The model registry to populate.

    Returns:
        Number of models registered.
    """
    count = 0

    # Try Ollama first
    ollama_available = False
    available_tags: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            available_tags = [
                m.get("name", "") for m in data.get("models", [])
            ]
            ollama_available = True
            logger.info(
                "Ollama is available with %d model(s): %s",
                len(available_tags), available_tags,
            )
    except Exception as exc:
        logger.warning("Ollama not available (%s), using fixture models", exc)

    if ollama_available and available_tags:
        # Register Ollama models that we have role definitions for
        for tag in available_tags:
            # Match against known roles (exact or prefix match)
            role = MODEL_ROLES.get(tag)
            if role is None:
                # Try prefix match (e.g., "qwen2.5:7b" matches "qwen2.5:latest")
                base_name = tag.split(":")[0]
                for role_tag, role_def in MODEL_ROLES.items():
                    if role_tag.startswith(base_name):
                        role = role_def
                        break

            if role:
                entry = ModelRegistryEntry(
                    **role,
                    runtime="ollama",
                    ollama_model=tag,
                )
                registry.register(entry)
                count += 1
                logger.info("Registered Ollama model: %s → %s", tag, role["name"])
            else:
                logger.debug("Skipping unknown Ollama model: %s", tag)

    if count == 0:
        # Fallback: register fixture models
        logger.info("Registering fixture fallback models")
        for fixture_def in FIXTURE_MODELS:
            entry = ModelRegistryEntry(**fixture_def)
            registry.register(entry)
            count += 1
            logger.info("Registered fixture model: %s", fixture_def["name"])

    logger.info("Seeded %d model(s) into registry", count)
    return count
