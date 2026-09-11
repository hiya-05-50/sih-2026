from __future__ import annotations

"""Sprint 4 – Flagship Pipeline API Endpoints.

Provides the ``/v1/flagship`` endpoints to execute the complete
flagship pipeline and retrieve execution results.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.decision_package import FlagshipExecutionResult
from app.services.flagship_pipeline import FlagshipPipeline
from shared.enums import UserRole

router = APIRouter(prefix="/v1/flagship", tags=["flagship"])

_pipeline: FlagshipPipeline | None = None


def configure(pipeline: FlagshipPipeline) -> None:
    """Inject the shared FlagshipPipeline singleton."""
    global _pipeline
    _pipeline = pipeline


def _get_pipeline() -> FlagshipPipeline:
    assert _pipeline is not None, "flagship router not configured"
    return _pipeline


@router.post("/execute", response_model=FlagshipExecutionResult)
async def execute_flagship(
    document_id: str | None = None,
    user_role: UserRole = UserRole.ENGINEER,
) -> FlagshipExecutionResult:
    """Execute the complete flagship pipeline.

    Runs:
      UPLOAD → OCR/VISION → EVIDENCE → RETRIEVAL → REASONING →
      DETERMINISTIC COMPUTE → VERIFICATION → RISK → APPROVAL → ARTIFACT

    Args:
        document_id: Optional document ID (will generate sample if not provided).
        user_role: Role of the executing user.
    """
    pipeline = _get_pipeline()
    result = await pipeline.execute(
        document_id=document_id,
        user_role=user_role,
    )
    return result


@router.get("/{task_id}", response_model=FlagshipExecutionResult)
async def get_flagship_execution(task_id: str) -> FlagshipExecutionResult:
    """Retrieve a flagship execution result by task ID."""
    pipeline = _get_pipeline()
    execution = pipeline.get_execution(task_id)
    if execution is None:
        raise HTTPException(
            status_code=404,
            detail=f"Flagship execution '{task_id}' not found",
        )
    return execution


@router.get("/", response_model=list[FlagshipExecutionResult])
async def list_flagship_executions() -> list[FlagshipExecutionResult]:
    """List all flagship pipeline executions."""
    return _get_pipeline().list_executions()
