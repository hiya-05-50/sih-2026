"""Sprint 1 – Adapter Manager.

Maps model IDs to live ModelAdapter instances.  Sprint 1 exclusively
uses FixtureModelAdapter; concrete inference adapters (Ollama, vLLM)
will be added in later sprints.
"""

from __future__ import annotations

from app.adapters.base import ModelAdapter
from app.adapters.fixture import FixtureModelAdapter
from app.schemas.adapter import HealthCheckResponse
from app.services.registry import ModelRegistry


class AdapterManager:
    """Factory and cache for model adapter instances.

    Each registered model gets a lazily-created adapter that is
    cached for the lifetime of the manager.

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

        # Sprint 1: all models use the FixtureModelAdapter.
        adapter = FixtureModelAdapter(registry_entry=entry)
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
