"""Sprint 1 – In-memory Model Registry.

Provides CRUD operations for ModelRegistryEntry objects.
Persistence is in-memory for Sprint 1; a database-backed
implementation will be introduced in a later sprint.
"""

from __future__ import annotations

from app.schemas.model_registry import ModelRegistryEntry
from shared.enums import ModelCapability


class ModelRegistry:
    """In-memory store for registered SAFIRE models.

    Thread-safety note: FastAPI runs request handlers on an
    asyncio event loop (single-threaded), so a plain dict is
    sufficient for Sprint 1.  A database-backed store in later
    sprints will handle concurrency at the DB level.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ModelRegistryEntry] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register(self, entry: ModelRegistryEntry) -> ModelRegistryEntry:
        """Add or overwrite a model entry.

        Args:
            entry: The model entry to register.

        Returns:
            The registered entry.
        """
        self._entries[entry.model_id] = entry
        return entry

    def get(self, model_id: str) -> ModelRegistryEntry | None:
        """Look up a model by its ID.

        Args:
            model_id: Unique model identifier.

        Returns:
            The entry if found, otherwise ``None``.
        """
        return self._entries.get(model_id)

    def list_all(self) -> list[ModelRegistryEntry]:
        """Return all registered model entries.

        Returns:
            A list of all entries (order is insertion-order).
        """
        return list(self._entries.values())

    def delete(self, model_id: str) -> bool:
        """Remove a model entry.

        Args:
            model_id: Unique model identifier.

        Returns:
            ``True`` if the entry was found and removed, ``False`` otherwise.
        """
        if model_id in self._entries:
            del self._entries[model_id]
            return True
        return False

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def find_by_capability(
        self, capability: ModelCapability
    ) -> list[ModelRegistryEntry]:
        """Return entries that include the given capability.

        Args:
            capability: The capability to filter by.

        Returns:
            Entries whose capabilities list contains *capability*.
        """
        return [
            entry
            for entry in self._entries.values()
            if capability in entry.capabilities
        ]
