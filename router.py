"""Sprint 1 – Model Router.

Selects the best registered model for a set of required capabilities
and constraints.  Uses a simple capability-match strategy with
optional benchmark-based ranking.
"""

from __future__ import annotations

from app.schemas.model_registry import ModelRegistryEntry
from app.schemas.routing import RouteRequest, RouteResponse
from app.services.registry import ModelRegistry


class ModelRouter:
    """Capability-based model selection engine.

    Routing strategy (Sprint 1):
    1. Filter models whose capabilities are a **superset** of the
       required capabilities.
    2. Filter by ``context_length >= min_context_length`` (if specified).
    3. Rank remaining candidates by benchmark latency (lower is better)
       when ``prefer_low_latency`` is set and profiles are available.
    4. Return the best match with a human-readable reasoning string.

    Args:
        registry: The model registry to query.
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def route(self, request: RouteRequest) -> RouteResponse | None:
        """Select the best model for the given routing request.

        Args:
            request: The routing request with required capabilities
                and constraints.

        Returns:
            A ``RouteResponse`` with the selected model, or ``None``
            if no model satisfies the requirements.
        """
        required = set(request.required_capabilities)
        candidates = [
            entry
            for entry in self._registry.list_all()
            if required.issubset(set(entry.capabilities))
        ]

        # Context-length filter
        if request.min_context_length is not None:
            candidates = [
                entry
                for entry in candidates
                if entry.context_length >= request.min_context_length
            ]

        if not candidates:
            return None

        # Rank
        selected = self._rank(candidates, request)

        reasoning_parts = [
            f"Model '{selected.name}' selected.",
            f"Matches all required capabilities: {', '.join(sorted(str(c) for c in required))}.",
        ]
        if request.min_context_length is not None:
            reasoning_parts.append(
                f"Context length {selected.context_length} >= required {request.min_context_length}."
            )
        if request.prefer_low_latency and self._get_latency(selected) is not None:
            reasoning_parts.append(
                f"Latency: {self._get_latency(selected):.1f} ms (lowest among candidates)."
            )

        return RouteResponse(
            model_id=selected.model_id,
            model_name=selected.name,
            capabilities=list(selected.capabilities),
            reasoning=" ".join(reasoning_parts),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rank(
        self,
        candidates: list[ModelRegistryEntry],
        request: RouteRequest,
    ) -> ModelRegistryEntry:
        """Pick the best candidate from a non-empty list."""
        if request.prefer_low_latency:
            # Sort by latency ascending; models without a profile go last.
            candidates = sorted(
                candidates,
                key=lambda e: (
                    self._get_latency(e) if self._get_latency(e) is not None else float("inf")
                ),
            )
        return candidates[0]

    @staticmethod
    def _get_latency(entry: ModelRegistryEntry) -> float | None:
        if entry.benchmark_profile is not None:
            return entry.benchmark_profile.latency_ms
        return None
