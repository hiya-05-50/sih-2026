"""Sprint 5 – Sovereignty Readiness Gate Tests.

Covers:
  - All controls healthy → VERIFIED
  - Each individual control failure → NOT VERIFIED
  - Self-test pass / failure → VERIFIED / NOT VERIFIED
  - Mandatory external dependency → NOT VERIFIED
  - Self-test not run yet → NOT VERIFIED
  - Readiness changes are logged
  - Self-test results are logged
  - ReadinessReport structure
"""

from __future__ import annotations

import pytest

from app.services.sovereignty.dns_monitor import DNSMonitor
from app.services.sovereignty.network_enforcer import NetworkEnforcer
from app.services.sovereignty.readiness_gate import (
    SOVEREIGNTY_NOT_VERIFIED,
    SOVEREIGNTY_VERIFIED,
    SovereigntyReadinessGate,
)
from app.services.sovereignty.sovereignty_logger import SovereigntyLogger
from shared.enums import SovereigntyEventType, SovereigntyState


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def sov_logger() -> SovereigntyLogger:
    return SovereigntyLogger(max_events=200)


@pytest.fixture
def enforcer(sov_logger: SovereigntyLogger) -> NetworkEnforcer:
    return NetworkEnforcer(sovereignty_logger=sov_logger)


@pytest.fixture
def dns_monitor(
    sov_logger: SovereigntyLogger,
    enforcer: NetworkEnforcer,
) -> DNSMonitor:
    return DNSMonitor(
        sovereignty_logger=sov_logger,
        network_enforcer=enforcer,
    )


@pytest.fixture
def full_gate(
    sov_logger: SovereigntyLogger,
    enforcer: NetworkEnforcer,
    dns_monitor: DNSMonitor,
) -> SovereigntyReadinessGate:
    """Gate with all controls wired — self-test still needs to be run."""
    return SovereigntyReadinessGate(
        sovereignty_logger=sov_logger,
        network_enforcer=enforcer,
        dns_monitor=dns_monitor,
        external_dependencies=[],
    )


# -----------------------------------------------------------------------
# All controls healthy → VERIFIED
# -----------------------------------------------------------------------


class TestAllControlsHealthy:

    def test_verified_after_self_test(self, full_gate):
        full_gate.run_self_test()
        report = full_gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_VERIFIED
        assert report.state == SovereigntyState.READY
        assert report.all_passed is True

    def test_all_conditions_pass(self, full_gate):
        full_gate.run_self_test()
        report = full_gate.check_readiness()
        for cond in report.conditions:
            assert cond.passed is True, f"{cond.name} should pass"

    def test_self_test_included_in_report(self, full_gate):
        full_gate.run_self_test()
        report = full_gate.check_readiness()
        assert report.self_test is not None
        assert report.self_test.passed is True


# -----------------------------------------------------------------------
# Self-test not run → NOT VERIFIED
# -----------------------------------------------------------------------


class TestSelfTestNotRun:

    def test_not_verified_without_self_test(self, full_gate):
        report = full_gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED
        assert report.all_passed is False

    def test_self_test_condition_fails(self, full_gate):
        report = full_gate.check_readiness()
        st_cond = [c for c in report.conditions if c.name == "self_test_passed"]
        assert len(st_cond) == 1
        assert st_cond[0].passed is False
        assert "not been run" in st_cond[0].detail


# -----------------------------------------------------------------------
# Each individual control failure → NOT VERIFIED
# -----------------------------------------------------------------------


class TestIndividualControlFailure:

    def test_no_enforcer(self, sov_logger, dns_monitor):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=None,
            dns_monitor=dns_monitor,
        )
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED
        failed = [c.name for c in report.conditions if not c.passed]
        assert "outbound_enforcement_active" in failed
        assert "deny_policy_active" in failed

    def test_no_dns_monitor(self, sov_logger, enforcer):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=enforcer,
            dns_monitor=None,
        )
        gate.run_self_test()
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED
        failed = [c.name for c in report.conditions if not c.passed]
        assert "dns_monitoring_active" in failed

    def test_external_dependency_present(self, full_gate, sov_logger, enforcer, dns_monitor):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=enforcer,
            dns_monitor=dns_monitor,
            external_dependencies=["cloud-api.example.com"],
        )
        gate.run_self_test()
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED
        dep_cond = [c for c in report.conditions if c.name == "no_external_dependency"]
        assert len(dep_cond) == 1
        assert dep_cond[0].passed is False
        assert "cloud-api.example.com" in dep_cond[0].detail


# -----------------------------------------------------------------------
# Self-test mechanics
# -----------------------------------------------------------------------


class TestSelfTest:

    def test_self_test_blocks_outbound(self, full_gate):
        result = full_gate.run_self_test()
        assert result.outbound_blocked is True

    def test_self_test_block_logged(self, full_gate):
        result = full_gate.run_self_test()
        assert result.block_logged is True

    def test_self_test_passes_with_enforcer(self, full_gate):
        result = full_gate.run_self_test()
        assert result.passed is True
        assert "PASSED" in result.detail

    def test_self_test_fails_without_enforcer(self, sov_logger):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=None,
        )
        result = gate.run_self_test()
        assert result.passed is False
        assert result.outbound_blocked is False

    def test_self_test_has_timestamp(self, full_gate):
        result = full_gate.run_self_test()
        assert "T" in result.timestamp


# -----------------------------------------------------------------------
# Self-test failure → NOT VERIFIED
# -----------------------------------------------------------------------


class TestSelfTestFailure:

    def test_failed_self_test_blocks_verification(self, sov_logger):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=None,
        )
        gate.run_self_test()  # will fail — no enforcer
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED


# -----------------------------------------------------------------------
# Mandatory external dependency → NOT VERIFIED
# -----------------------------------------------------------------------


class TestExternalDependency:

    def test_single_dependency(self, sov_logger, enforcer, dns_monitor):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=enforcer,
            dns_monitor=dns_monitor,
            external_dependencies=["api.openai.com"],
        )
        gate.run_self_test()
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED

    def test_multiple_dependencies(self, sov_logger, enforcer, dns_monitor):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=enforcer,
            dns_monitor=dns_monitor,
            external_dependencies=["api.openai.com", "cloud.google.com"],
        )
        gate.run_self_test()
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED

    def test_empty_dependencies_ok(self, full_gate):
        full_gate.run_self_test()
        report = full_gate.check_readiness()
        dep_cond = [c for c in report.conditions if c.name == "no_external_dependency"]
        assert dep_cond[0].passed is True


# -----------------------------------------------------------------------
# Logging verification
# -----------------------------------------------------------------------


class TestLogging:

    def test_readiness_change_logged(self, full_gate, sov_logger):
        full_gate.run_self_test()
        full_gate.check_readiness()
        events = sov_logger.get_events(
            event_type=SovereigntyEventType.READINESS_CHANGE
        )
        assert len(events) >= 1
        assert SOVEREIGNTY_VERIFIED in events[0].detail

    def test_self_test_result_logged(self, full_gate, sov_logger):
        full_gate.run_self_test()
        events = sov_logger.get_events(
            event_type=SovereigntyEventType.SELF_TEST_RESULT
        )
        assert len(events) >= 1
        assert events[0].metadata["passed"] is True

    def test_failed_readiness_logged_as_warning(self, sov_logger):
        gate = SovereigntyReadinessGate(
            sovereignty_logger=sov_logger,
            network_enforcer=None,
        )
        gate.check_readiness()
        events = sov_logger.get_events(
            event_type=SovereigntyEventType.READINESS_CHANGE
        )
        assert len(events) >= 1
        assert SOVEREIGNTY_NOT_VERIFIED in events[0].detail


# -----------------------------------------------------------------------
# Report structure
# -----------------------------------------------------------------------


class TestReportStructure:

    def test_report_has_six_conditions(self, full_gate):
        report = full_gate.check_readiness()
        assert len(report.conditions) == 6

    def test_report_has_timestamp(self, full_gate):
        report = full_gate.check_readiness()
        assert "T" in report.timestamp

    def test_condition_names(self, full_gate):
        report = full_gate.check_readiness()
        names = {c.name for c in report.conditions}
        assert names == {
            "outbound_enforcement_active",
            "deny_policy_active",
            "dns_monitoring_active",
            "outbound_monitoring_active",
            "no_external_dependency",
            "self_test_passed",
        }

    def test_not_verified_is_default(self):
        """A bare gate with nothing wired must never be VERIFIED."""
        sov_logger = SovereigntyLogger()
        gate = SovereigntyReadinessGate(sovereignty_logger=sov_logger)
        report = gate.check_readiness()
        assert report.sovereignty_status == SOVEREIGNTY_NOT_VERIFIED
        assert report.state == SovereigntyState.NOT_READY
