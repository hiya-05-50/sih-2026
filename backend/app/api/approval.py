from __future__ import annotations

"""Sprint 4 – Approval API Endpoints.

Provides the approval gate API under ``/v1/tasks/{task_id}/approval``.
Enforces the backend invariant: only APPROVER/ADMIN can approve AMBER/RED tasks.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.decision_package import ApprovalDecision, ApprovalRequest
from app.services.approval import ApprovalService

router = APIRouter(tags=["approval"])

_approval_service: ApprovalService | None = None


def configure(approval_service: ApprovalService) -> None:
    """Inject the shared ApprovalService singleton."""
    global _approval_service
    _approval_service = approval_service


def _get_service() -> ApprovalService:
    assert _approval_service is not None, "approval router not configured"
    return _approval_service


@router.post(
    "/v1/tasks/{task_id}/approve",
    response_model=ApprovalDecision,
)
async def approve_task(task_id: str, request: ApprovalRequest) -> ApprovalDecision:
    """Approve or reject a task.

    Only APPROVER or ADMIN roles can approve AMBER/RED risk tasks.
    ENGINEER role attempts will receive 403 Forbidden.
    """
    service = _get_service()
    try:
        result = service.decide(task_id, request)
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/v1/tasks/{task_id}/approval-status",
    response_model=ApprovalDecision,
)
async def get_approval_status(task_id: str) -> ApprovalDecision:
    """Get the current approval status for a task."""
    service = _get_service()
    decision = service.get_approval(task_id)
    if decision is None:
        raise HTTPException(
            status_code=404,
            detail=f"No approval record for task '{task_id}'",
        )
    return decision
