from __future__ import annotations

"""Sprint 5 – SIAB Benchmark API Endpoints.

Provides ``/v1/siab`` endpoints for running and retrieving SIAB
benchmark results.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.services.siab import SIABReport, SIABRunner

router = APIRouter(prefix="/v1/siab", tags=["siab"])

_runner: SIABRunner | None = None


def configure(runner: SIABRunner) -> None:
    """Inject the shared SIABRunner singleton."""
    global _runner
    _runner = runner


def _get_runner() -> SIABRunner:
    assert _runner is not None, "SIAB router not configured"
    return _runner


@router.post("/run", response_model=SIABReport)
async def run_siab_benchmark() -> SIABReport:
    """Execute the full 3-configuration SIAB benchmark.

    Configs:
      1. Single model baseline (no scaffolding)
      2. Agent + tools (no verification)
      3. Full SAFIRE pipeline

    All metrics use 'TO BE VALIDATED' until actually measured.
    """
    runner = _get_runner()
    return await runner.run_benchmark()


@router.get("/results", response_model=List[SIABReport])
async def list_siab_results() -> List[SIABReport]:
    """List all SIAB benchmark reports."""
    return _get_runner().get_reports()


@router.get("/latest", response_model=SIABReport)
async def get_latest_siab_result() -> SIABReport:
    """Get the most recent SIAB benchmark report."""
    report = _get_runner().get_latest_report()
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No SIAB benchmark has been run yet",
        )
    return report
