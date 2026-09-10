"""Sprint 1 – Adapter Manager.

Maps model IDs to live ModelAdapter instances.  Dispatches between
OllamaModelAdapter (real inference) and FixtureModelAdapter (testing)
based on the registry entry's ``runtime`` field.
"""

from __future__ import annotations

import logging

from app.adapters.base import ModelAdapter
from app.adapters.fixture import FixtureModelAdapter
from app.schemas.adapter import HealthCheckResponse
from app.services.registry import ModelRegistry

logger = logging.getLogger(__name__)


class AdapterManager:
    """Factory and cache for model adapter instances.

    Each registered model gets a lazily-created adapter that is
    cached for the lifetime of the manager.  The adapter type is
    determined by the ``runtime`` field on the registry entry:

    - ``"ollama"`` → ``OllamaModelAdapter`` (real local inference)
    - ``"fixture"`` / ``None`` → ``FixtureModelAdapter`` (deterministic)

    Args:
        registry: The model registry to look up entries from.
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry
        self._adapters: dict[str, ModelAdapter] = {}

    # ------------------------------------------------------------------
    # Adapter access
    # ------------------------------------------------------------------

    def get_adapter(self, model_id: str) -> ModelAdapter | None:
        """Return the adapter for *model_id*, creating it if necessary.

        Args:
            model_id: Unique model identifier.

        Returns:
            The adapter instance, or ``None`` if the model is not
            registered.
        """
        if model_id in self._adapters:
            return self._adapters[model_id]

        entry = self._registry.get(model_id)
        if entry is None:
            return None

        # Dispatch based on runtime field
        runtime = (entry.runtime or "fixture").lower()
        if runtime == "ollama":
            # Lazy import to avoid import errors when httpx isn't needed
            from app.adapters.ollama import OllamaModelAdapter
            adapter: ModelAdapter = OllamaModelAdapter(registry_entry=entry)
            logger.info(
                "Created OllamaModelAdapter for '%s' (model: %s)",
                model_id, entry.ollama_model,
            )
        else:
            adapter = FixtureModelAdapter(registry_entry=entry)
            logger.debug("Created FixtureModelAdapter for '%s'", model_id)

        self._adapters[model_id] = adapter
        return adapter

    def remove_adapter(self, model_id: str) -> None:
        """Remove the cached adapter for *model_id* (if any).

        Called when a model is deleted from the registry.
        """
        self._adapters.pop(model_id, None)

    # ------------------------------------------------------------------
    # Operational
    # ------------------------------------------------------------------

    async def health_check_all(self) -> dict[str, HealthCheckResponse]:
        """Run health checks on every active adapter.

        Returns:
            A mapping of ``model_id`` → ``HealthCheckResponse``.
        """
        results: dict[str, HealthCheckResponse] = {}
        for model_id, adapter in self._adapters.items():
            results[model_id] = await adapter.health_check()
        return results
