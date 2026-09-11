"""Sprint 1 – Model Router.

Selects the best registered model for a given routing request using
the deterministic 5-step pipeline defined in Master PRD §14:

    1. Capability filter   — models must be a superset of required caps
    2. Feasibility filter  — VRAM footprint must fit within available VRAM
    3. Candidate scoring   — composite score from latency, VRAM, capability coverage
    4. Selection           — pick the top-scored candidate
    5. Fallback            — graceful degradation when no model fits
"""

from __future__ import annotations

import logging
from typing import Optional

from app.schemas.model_registry import ModelRegistryEntry
from app.schemas.routing import RouteCandidate, RouteRequest, RouteResponse
from app.services.registry import ModelRegistry

logger = logging.getLogger(__name__)

# Scoring weights (sum to 1.0)
_W_LATENCY = 0.5
_W_VRAM = 0.3
_W_CAPABILITY = 0.2


class ModelRouter:
    """Deterministic 5-step model selection engine.

    The routing pipeline is designed to be reproducible: given the
    same registry state and request, the same model is always selected.
    The reasoning string is human-readable and judge-visible.

    Args:
        registry: The model registry to query.
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def route(self, request: RouteRequest) -> RouteResponse | None:
        """Select the best model for the given routing request.

        Implements the full 5-step pipeline per Master PRD §14.

        Args:
            request: The routing request with required capabilities
                and constraints.

        Returns:
            A ``RouteResponse`` with the selected model and full
            scoring breakdown, or ``None`` if no model satisfies
            the requirements even after fallback.
        """
        required = set(request.required_capabilities)
        reasoning_parts: list[str] = []

        # ---- Step 1: Capability filter ----
        candidates = [
            entry
            for entry in self._registry.list_all()
            if required.issubset(set(entry.capabilities))
        ]
        reasoning_parts.append(
            f"Step 1 (capability filter): {len(candidates)} model(s) "
            f"match required capabilities "
            f"[{', '.join(sorted(str(c) for c in required))}]."
        )

        # Context-length filter (part of capability filtering)
        if request.min_context_length is not None:
            candidates = [
                entry
                for entry in candidates
                if entry.context_length >= request.min_context_length
            ]
            reasoning_parts.append(
                f"Context-length filter: {len(candidates)} model(s) "
                f"meet min context length {request.min_context_length}."
            )

        # ---- Step 2: Feasibility filter (VRAM) ----
        if request.available_vram_mb is not None:
            pre_count = len(candidates)
            feasible = [
                entry
                for entry in candidates
                if entry.vram_footprint is None  # unknown = assume feasible
                or (entry.vram_footprint * 1024) <= request.available_vram_mb
            ]
            infeasible_count = pre_count - len(feasible)
            if infeasible_count > 0:
                reasoning_parts.append(
                    f"Step 2 (feasibility filter): excluded {infeasible_count} "
                    f"model(s) exceeding available VRAM "
                    f"({request.available_vram_mb:.0f} MB)."
                )
            candidates = feasible
        else:
            reasoning_parts.append(
                "Step 2 (feasibility filter): skipped (no VRAM constraint)."
            )

        if not candidates:
            # ---- Step 5: Fallback ----
            return self._fallback(request, required, reasoning_parts)

        # ---- Step 3: Candidate scoring ----
        scored = self._score_candidates(candidates, request)

        # ---- Step 4: Selection ----
        scored.sort(key=lambda c: c.score, reverse=True)
        best = scored[0]
        selected = self._registry.get(best.model_id)

        if selected is None:
            return None

        reasoning_parts.append(
            f"Step 3 (scoring): top candidate '{selected.name}' "
            f"scored {best.score:.3f} "
            f"(latency={best.latency_score:.3f}, "
            f"vram={best.vram_score:.3f}, "
            f"capability={best.capability_score:.3f})."
        )
        reasoning_parts.append(
            f"Step 4 (selection): model '{selected.name}' selected."
        )

        return RouteResponse(
            model_id=selected.model_id,
            model_name=selected.name,
            capabilities=list(selected.capabilities),
            reasoning=" ".join(reasoning_parts),
            candidates=[c for c in scored[:5]],  # top 5 for transparency
        )

    # ------------------------------------------------------------------
    # Step 3: Scoring
    # ------------------------------------------------------------------

    def _score_candidates(
        self,
        candidates: list[ModelRegistryEntry],
        request: RouteRequest,
    ) -> list[RouteCandidate]:
        """Score each candidate with a composite metric."""
        required = set(request.required_capabilities)
        scored: list[RouteCandidate] = []

        # Collect latency values for normalization
        latencies = [
            self._get_latency(e) for e in candidates
            if self._get_latency(e) is not None
        ]
        max_latency = max(latencies) if latencies else 1.0

        for entry in candidates:
            # Latency score: lower is better, normalized 0–1
            latency = self._get_latency(entry)
            if latency is not None and max_latency > 0:
                latency_score = 1.0 - (latency / max_latency)
            else:
                latency_score = 0.5  # neutral for unmeasured

            # VRAM score: less VRAM = more room, normalized 0–1
            if entry.vram_footprint is not None and entry.vram_footprint > 0:
                # 8GB = 8192MB reference; smaller footprint = better
                vram_score = max(0.0, 1.0 - (entry.vram_footprint / 8.0))
            else:
                vram_score = 0.5  # neutral for unmeasured

            # Capability coverage: extra capabilities are a bonus
            entry_caps = set(entry.capabilities)
            extra_caps = len(entry_caps - required)
            total_caps = len(entry_caps)
            capability_score = min(1.0, 0.5 + (extra_caps / max(total_caps, 1)) * 0.5)

            # Composite score
            if request.prefer_low_latency:
                # Boost latency weight when requested
                score = (
                    0.7 * latency_score
                    + 0.15 * vram_score
                    + 0.15 * capability_score
                )
            else:
                score = (
                    _W_LATENCY * latency_score
                    + _W_VRAM * vram_score
                    + _W_CAPABILITY * capability_score
                )

            scored.append(RouteCandidate(
                model_id=entry.model_id,
                model_name=entry.name,
                score=round(score, 4),
                latency_score=round(latency_score, 4),
                vram_score=round(vram_score, 4),
                capability_score=round(capability_score, 4),
            ))

        return scored

    # ------------------------------------------------------------------
    # Step 5: Fallback
    # ------------------------------------------------------------------

    def _fallback(
        self,
        request: RouteRequest,
        required: set,
        reasoning_parts: list[str],
    ) -> RouteResponse | None:
        """Attempt graceful fallback when no candidate passes all filters.

        Fallback strategy:
        1. Relax capability requirements to TEXT-only
        2. If still nothing, return None with explanation
        """
        reasoning_parts.append(
            "Step 5 (fallback): no candidate passed all filters."
        )

        # Try relaxing to any model with TEXT capability
        all_models = self._registry.list_all()
        text_models = [
            e for e in all_models
            if "TEXT" in [str(c) for c in e.capabilities]
        ]

        if text_models:
            # Pick first text model as fallback
            fallback = text_models[0]
            reasoning_parts.append(
                f"Fallback: relaxed to TEXT-only model '{fallback.name}'. "
                f"Original requirements [{', '.join(sorted(str(c) for c in required))}] "
                f"could not be fully satisfied."
            )

            return RouteResponse(
                model_id=fallback.model_id,
                model_name=fallback.name,
                capabilities=list(fallback.capabilities),
                reasoning=" ".join(reasoning_parts),
                candidates=[RouteCandidate(
                    model_id=fallback.model_id,
                    model_name=fallback.name,
                    score=0.0,
                    latency_score=0.0,
                    vram_score=0.0,
                    capability_score=0.0,
                )],
            )

        reasoning_parts.append(
            "Fallback exhausted: no models available in registry."
        )
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_latency(entry: ModelRegistryEntry) -> float | None:
        if entry.benchmark_profile is not None:
            # Prefer warm inference latency, fall back to general latency
            if entry.benchmark_profile.warm_inference_latency_ms is not None:
                return entry.benchmark_profile.warm_inference_latency_ms
            return entry.benchmark_profile.latency_ms
        return None
