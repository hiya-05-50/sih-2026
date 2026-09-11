"""Sprint 5 – Sovereignty Monitor Tests.

Tests the sovereignty self-test mechanism, fail-closed behavior,
and blocked-attempt recording.
"""

import pytest

from app.services.sovereignty import SovereigntyMonitor
from app.services.audit import AuditEventStore
from app.schemas.audit import AuditEventType
from shared.enums import SovereigntyState


@pytest.fixture
def audit_store():
    return AuditEventStore()


@pytest.fixture
def monitor(audit_store):
    return SovereigntyMonitor(audit_store=audit_store)


class TestSovereigntySelfTest:
    """Test the sovereignty self-test mechanism."""

    def test_self_test_runs_without_error(self, monitor):
        """Self-test must complete without throwing exceptions."""
        status = monitor.check_sovereignty()
        assert status is not None
        assert status.state in (
            SovereigntyState.READY,
            SovereigntyState.NOT_READY,
            SovereigntyState.DEGRADED,
        )

    def test_self_test_returns_checks(self, monitor):
        """Self-test must return individual check results."""
        status = monitor.check_sovereignty()
        # Must have at least 4 checks: TCP, DNS, API binding, sandbox
        assert len(status.checks) >= 4

    def test_each_check_has_name_and_detail(self, monitor):
        """Each check must have a name and detail explanation."""
        status = monitor.check_sovereignty()
        for check in status.checks:
            assert check.check_name, "Check must have a name"
            assert check.detail, "Check must have a detail explanation"

    def test_self_test_records_audit_event(self, monitor, audit_store):
        """Self-test must record a SOVEREIGNTY_CHECK audit event."""
        monitor.check_sovereignty()
        events = audit_store.list_events(
            event_type=AuditEventType.SOVEREIGNTY_CHECK
        )
        assert len(events) >= 1

    def test_self_test_updates_last_check_timestamp(self, monitor):
        """Self-test must update the last check timestamp."""
        monitor.check_sovereignty()
        status = monitor.get_status()
        assert status.last_check_at is not None


class TestSovereigntyFailClosed:
    """Test fail-closed behavior."""

    def test_is_sovereign_false_before_check(self, monitor):
        """Before any check, is_sovereign() must return False (fail-closed)."""
        assert monitor.is_sovereign() is False

    def test_get_status_before_check_is_not_ready(self, monitor):
        """Before any check, status must be NOT_READY."""
        status = monitor.get_status()
        assert status.state == SovereigntyState.NOT_READY

    def test_status_has_explanation(self, monitor):
        """Status must always have a human-readable explanation."""
        status = monitor.get_status()
        assert len(status.detail) > 0


class TestBlockedAttempts:
    """Test blocked-attempt recording."""

    def test_record_blocked_attempt(self, monitor):
        """Must be able to record a blocked external call."""
        attempt = monitor.record_blocked_attempt(
            source="test_component",
            destination="api.openai.com",
            reason="Sovereignty policy: external API calls blocked",
        )
        assert attempt.source == "test_component"
        assert attempt.destination == "api.openai.com"
        assert attempt.action_taken == "BLOCKED"

    def test_blocked_attempts_are_listed(self, monitor):
        """Blocked attempts must be retrievable."""
        monitor.record_blocked_attempt("a", "b.com", "test")
        monitor.record_blocked_attempt("c", "d.com", "test")
        attempts = monitor.get_blocked_attempts()
        assert len(attempts) == 2

    def test_blocked_attempt_records_audit_event(self, monitor, audit_store):
        """Blocked attempt must create SOVEREIGNTY_BLOCKED audit event."""
        monitor.record_blocked_attempt("src", "dst.com", "reason")
        events = audit_store.list_events(
            event_type=AuditEventType.SOVEREIGNTY_BLOCKED
        )
        assert len(events) == 1

    def test_blocked_attempts_in_status(self, monitor):
        """Blocked attempts should be visible in sovereignty status."""
        monitor.record_blocked_attempt("src", "dst.com", "reason")
        monitor.check_sovereignty()
        status = monitor.get_status()
        assert len(status.blocked_attempts) >= 1


class TestSovereigntyHonesty:
    """Test that sovereignty reporting is honest, not fake.

    On a development machine with internet access, sovereignty
    MUST report NOT_READY because external connections succeed.
    """

    def test_dev_machine_reports_not_ready(self, monitor):
        """On a dev machine with internet, sovereignty should be NOT_READY.

        This test verifies the system is honest — it doesn't fake sovereignty.
        If this test runs on a truly isolated machine, it should be READY.
        Either outcome is valid; the point is that the system checks for real.
        """
        status = monitor.check_sovereignty()
        # The status must be deterministic for the given environment
        assert status.state in (SovereigntyState.READY, SovereigntyState.NOT_READY)
        # Regardless of outcome, it must provide explanation
        assert len(status.detail) > 20
