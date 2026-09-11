"""Sprint 4 – Approval Service Tests.

Tests the backend-enforced approval invariant:
  risk ∈ {AMBER, RED} AND approval_status != APPROVED → artifact delivery DENIED

Key tests:
  - APPROVER can approve AMBER/RED
  - ENGINEER cannot approve (PermissionError)
  - Artifact delivery blocked when not approved
  - GREEN risk bypasses approval gate
"""

import pytest
from app.services.approval import ApprovalService
from app.schemas.decision_package import ApprovalRequest
from shared.enums import ApprovalStatus, RiskLevel, UserRole


@pytest.fixture
def service():
    return ApprovalService()


class TestApprovalDecisions:
    """Test approval/rejection logic."""

    def test_approver_can_approve_amber(self, service):
        service.request_approval("task-1", RiskLevel.AMBER)
        request = ApprovalRequest(
            user_id="approver-1",
            user_role=UserRole.APPROVER,
            action=ApprovalStatus.APPROVED,
            reason="All checks passed",
        )
        decision = service.decide("task-1", request)
        assert decision.status == ApprovalStatus.APPROVED
        assert decision.decided_by == "approver-1"
        assert decision.decided_by_role == UserRole.APPROVER

    def test_admin_can_approve_red(self, service):
        service.request_approval("task-2", RiskLevel.RED)
        request = ApprovalRequest(
            user_id="admin-1",
            user_role=UserRole.ADMIN,
            action=ApprovalStatus.APPROVED,
            reason="Override",
        )
        decision = service.decide("task-2", request)
        assert decision.status == ApprovalStatus.APPROVED

    def test_engineer_cannot_approve(self, service):
        """THE INVARIANT: ENGINEER role cannot approve."""
        service.request_approval("task-3", RiskLevel.AMBER)
        request = ApprovalRequest(
            user_id="engineer-1",
            user_role=UserRole.ENGINEER,
            action=ApprovalStatus.APPROVED,
            reason="Attempting bypass",
        )
        with pytest.raises(PermissionError, match="ENGINEER role cannot approve"):
            service.decide("task-3", request)

    def test_engineer_can_reject(self, service):
        """Engineers can reject (flag issues) but cannot approve."""
        service.request_approval("task-4", RiskLevel.AMBER)
        request = ApprovalRequest(
            user_id="engineer-1",
            user_role=UserRole.ENGINEER,
            action=ApprovalStatus.REJECTED,
            reason="Found issues",
        )
        decision = service.decide("task-4", request)
        assert decision.status == ApprovalStatus.REJECTED

    def test_nonexistent_task_raises(self, service):
        request = ApprovalRequest(
            user_id="user-1",
            user_role=UserRole.APPROVER,
            action=ApprovalStatus.APPROVED,
        )
        with pytest.raises(ValueError, match="No approval request found"):
            service.decide("nonexistent", request)


class TestDeliveryGate:
    """Test the backend-enforced delivery invariant."""

    def test_green_allows_delivery(self, service):
        allowed, reason = service.check_delivery_allowed("task-green", RiskLevel.GREEN)
        assert allowed is True
        assert "GREEN" in reason

    def test_amber_without_approval_denies(self, service):
        """AMBER risk without approval → DENIED."""
        allowed, reason = service.check_delivery_allowed("task-no-approval", RiskLevel.AMBER)
        assert allowed is False
        assert "DENIED" in reason

    def test_amber_with_pending_denies(self, service):
        """AMBER risk with PENDING status → DENIED."""
        service.request_approval("task-pending", RiskLevel.AMBER)
        allowed, reason = service.check_delivery_allowed("task-pending", RiskLevel.AMBER)
        assert allowed is False
        assert "PENDING" in reason

    def test_amber_with_approval_allows(self, service):
        """AMBER risk with APPROVED status → ALLOWED."""
        service.request_approval("task-approved", RiskLevel.AMBER)
        service.decide("task-approved", ApprovalRequest(
            user_id="approver-1",
            user_role=UserRole.APPROVER,
            action=ApprovalStatus.APPROVED,
        ))
        allowed, reason = service.check_delivery_allowed("task-approved", RiskLevel.AMBER)
        assert allowed is True
        assert "ALLOWED" in reason

    def test_red_with_rejected_denies(self, service):
        """RED risk with REJECTED status → DENIED."""
        service.request_approval("task-rejected", RiskLevel.RED)
        service.decide("task-rejected", ApprovalRequest(
            user_id="approver-1",
            user_role=UserRole.APPROVER,
            action=ApprovalStatus.REJECTED,
            reason="Issues found",
        ))
        allowed, reason = service.check_delivery_allowed("task-rejected", RiskLevel.RED)
        assert allowed is False

    def test_amber_with_engineer_approval_denies(self, service):
        """Even if somehow an ENGINEER's approval got through, delivery is still denied."""
        # Directly manipulate to simulate a bug where engineer approval slipped through
        service.request_approval("task-eng-bypass", RiskLevel.AMBER)
        decision = service.get_approval("task-eng-bypass")
        decision.status = ApprovalStatus.APPROVED
        decision.decided_by = "engineer-sneaky"
        decision.decided_by_role = UserRole.ENGINEER

        allowed, reason = service.check_delivery_allowed("task-eng-bypass", RiskLevel.AMBER)
        assert allowed is False
        assert "ENGINEER" in reason or "invalid" in reason.lower()
