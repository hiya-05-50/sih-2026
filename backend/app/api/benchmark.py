"""Sprint 1 – Benchmark API endpoints.

Provides endpoints to trigger and retrieve benchmark measurements
for registered models.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.model_registry import BenchmarkProfile
from app.services.benchmark import BenchmarkRunner

router = APIRouter(prefix="/v1/benchmark", tags=["benchmark"])

_runner: BenchmarkRunner | None = None


def configure(runner: BenchmarkRunner) -> None:
    """Inject the shared BenchmarkRunner singleton."""
    global _runner  # noqa: PLW0603
    _runner = runner


def _get_runner() -> BenchmarkRunner:
    assert _runner is not None, "benchmark router not configured"
    return _runner


@router.post("/{model_id}", response_model=BenchmarkProfile)
async def run_benchmark(model_id: str) -> BenchmarkProfile:
    """Run the full benchmark suite on a model.

    Measures cold-start latency, warm-inference latency, VRAM usage,
    and throughput.  Results are stored in the model's registry entry.
    """
    try:
        profile = await _get_runner().benchmark(model_id)
        return profile
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark failed: {exc}",
        )
