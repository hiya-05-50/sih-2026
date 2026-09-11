from __future__ import annotations

"""Sprint 4 – Approval Service.

Implements the backend-enforced approval invariant per Master PRD §27 / Sprint Plan §10:
  risk ∈ {AMBER, RED} AND approval_status != APPROVED → artifact delivery DENIED

This is enforced at the API layer, not just the UI. An ENGINEER-role user
cannot approve and cannot force delivery around this check.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from app.schemas.decision_package import ApprovalDecision, ApprovalRequest
from shared.enums import ApprovalStatus, RiskLevel, UserRole

logger = logging.getLogger(__name__)


class ApprovalService:
    """Backend-enforced approval gate.

    The invariant: if risk is AMBER or RED, artifact delivery is DENIED
    unless an APPROVER (or ADMIN) has explicitly approved the task.
    """

    def __init__(self) -> None:
        self._decisions: Dict[str, ApprovalDecision] = {}

    def get_approval(self, task_id: str) -> Optional[ApprovalDecision]:
        """Get the current approval decision for a task."""
        return self._decisions.get(task_id)

    def request_approval(
        self, task_id: str, risk_level: RiskLevel
    ) -> ApprovalDecision:
        """Create a pending approval request for a task."""
        decision = ApprovalDecision(
            task_id=task_id,
            status=ApprovalStatus.PENDING,
            risk_level=risk_level,
        )
        self._decisions[task_id] = decision
        logger.info("Approval requested for task %s (risk=%s)", task_id, risk_level)
        return decision

    def decide(
        self, task_id: str, request: ApprovalRequest
    ) -> ApprovalDecision:
        """Process an approval/rejection decision.

        Enforces:
        - Only APPROVER or ADMIN roles can approve AMBER/RED tasks
        - ENGINEER role cannot approve
        - Decision is recorded with full audit trail

        Raises:
            PermissionError: if user role is insufficient
            ValueError: if no pending approval exists
        """
        existing = self._decisions.get(task_id)
        if existing is None:
            raise ValueError(f"No approval request found for task '{task_id}'")

        # --- Role enforcement ---
        if request.action == ApprovalStatus.APPROVED:
            if request.user_role == UserRole.ENGINEER:
                raise PermissionError(
                    f"ENGINEER role cannot approve tasks. "
                    f"Only APPROVER or ADMIN may approve. "
                    f"User '{request.user_id}' denied."
                )
            if request.user_role not in (UserRole.APPROVER, UserRole.ADMIN):
                raise PermissionError(
                    f"Role {request.user_role} cannot approve tasks"
                )

        # --- Record decision ---
        existing.status = request.action
        existing.decided_by = request.user_id
        existing.decided_by_role = request.user_role
        existing.reason = request.reason
        existing.decided_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Task %s %s by %s (%s): %s",
            task_id, request.action, request.user_id, request.user_role, request.reason,
        )
        return existing

    def check_delivery_allowed(
        self, task_id: str, risk_level: RiskLevel
    ) -> tuple[bool, str]:
        """Check whether artifact delivery is allowed.

        THE BACKEND INVARIANT:
            risk ∈ {AMBER, RED} AND approval_status != APPROVED → DENIED

        Returns:
            (allowed, reason) tuple.
        """
        if risk_level == RiskLevel.GREEN:
            return True, "GREEN risk — delivery allowed without approval"

        decision = self._decisions.get(task_id)
        if decision is None:
            return False, (
                f"Delivery DENIED: {risk_level} risk task requires approval, "
                f"but no approval request exists"
            )

        if decision.status != ApprovalStatus.APPROVED:
            return False, (
                f"Delivery DENIED: {risk_level} risk task has status "
                f"'{decision.status}', requires APPROVED"
            )

        # Verify the approver had the right role
        if decision.decided_by_role not in (UserRole.APPROVER, UserRole.ADMIN):
            return False, (
                f"Delivery DENIED: approval by {decision.decided_by_role} "
                f"is invalid — only APPROVER/ADMIN may approve {risk_level} risk"
            )

        return True, (
            f"Delivery ALLOWED: {risk_level} risk approved by "
            f"{decision.decided_by_role} ({decision.decided_by})"
        )
