from __future__ import annotations

"""Sprint 7 – Demo Sequence API.

Exposes the 21-step judge demo sequence as REST endpoints for
rehearsal and live demonstration.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.services.demo_sequence import (
    DemoSequenceResult,
    DemoSequenceRunner,
    DemoStepResult,
)

router = APIRouter(prefix="/v1/demo/sequence", tags=["demo-sequence"])

_runner: DemoSequenceRunner | None = None


def configure(runner: DemoSequenceRunner) -> None:
    """Inject the demo sequence runner."""
    global _runner
    _runner = runner


@router.post("/run", response_model=DemoSequenceResult)
async def run_demo_sequence() -> DemoSequenceResult:
    """Execute the full 21-step judge demo sequence.

    Each step exercises real system components.
    Results are stored for retrieval.

    The Sprint 6 acceptance gate requires this to pass twice
    back-to-back without unexplained failure.
    """
    assert _runner is not None, "DemoSequenceRunner not configured"
    return await _runner.run_full_sequence()


@router.get("/latest", response_model=DemoSequenceResult)
def get_latest_result() -> DemoSequenceResult:
    """Get the most recent demo sequence result."""
    assert _runner is not None, "DemoSequenceRunner not configured"
    result = _runner.get_latest_result()
    if result is None:
        raise HTTPException(status_code=404, detail="No demo sequence has been run yet")
    return result


@router.get("/results", response_model=List[DemoSequenceResult])
def list_all_results() -> List[DemoSequenceResult]:
    """List all demo sequence results."""
    assert _runner is not None, "DemoSequenceRunner not configured"
    return _runner.get_all_results()


@router.get("/step/{step_number}", response_model=DemoStepResult)
def get_step_result(step_number: int, run_index: int = -1) -> DemoStepResult:
    """Get a specific step result from a demo run.

    Args:
        step_number: Step number (1-21).
        run_index: Run index (-1 for latest, 0 for first, etc.).
    """
    assert _runner is not None, "DemoSequenceRunner not configured"
    results = _runner.get_all_results()
    if not results:
        raise HTTPException(status_code=404, detail="No demo runs available")

    if run_index < 0:
        run_index = len(results) + run_index
    if run_index < 0 or run_index >= len(results):
        raise HTTPException(status_code=404, detail=f"Run index {run_index} out of range")

    step = _runner.get_step_result(run_index, step_number)
    if step is None:
        raise HTTPException(status_code=404, detail=f"Step {step_number} not found in run {run_index}")
    return step
