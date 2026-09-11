"""Sprint 5 – Network Enforcement Tests.

Covers:
  - Zone A (loopback) classification and allowance
  - Zone B (trusted on-prem allowlist) behaviour
  - Zone C (external) default denial
  - Logging of blocked attempts through SovereigntyLogger
  - Unknown / invalid destinations defaulting to DENY
  - DNS monitor integration
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.sovereignty.dns_monitor import DNSMonitor
from app.services.sovereignty.network_enforcer import NetworkEnforcer
from app.services.sovereignty.sovereignty_logger import SovereigntyLogger
from shared.enums import (
    NetworkZone,
    SovereigntyEventSeverity,
    SovereigntyEventType,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def sov_logger() -> SovereigntyLogger:
    """Fresh sovereignty logger for each test."""
    return SovereigntyLogger(max_events=200)


@pytest.fixture
def enforcer(sov_logger: SovereigntyLogger) -> NetworkEnforcer:
    """Enforcer with two sample trusted hosts."""
    return NetworkEnforcer(
        sovereignty_logger=sov_logger,
        trusted_hosts=["192.168.1.100", "10.0.0.5"],
    )


@pytest.fixture
def dns_monitor(
    sov_logger: SovereigntyLogger,
    enforcer: NetworkEnforcer,
) -> DNSMonitor:
    return DNSMonitor(
        sovereignty_logger=sov_logger,
        network_enforcer=enforcer,
    )


# -----------------------------------------------------------------------
# Zone A — Loopback
# -----------------------------------------------------------------------


class TestZoneALoopback:
    """Zone A (loopback) must always be classified and allowed."""

    def test_127_0_0_1(self, enforcer: NetworkEnforcer):
        assert enforcer.classify_zone("127.0.0.1") == NetworkZone.LOOPBACK

    def test_localhost(self, enforcer: NetworkEnforcer):
        assert enforcer.classify_zone("localhost") == NetworkZone.LOOPBACK

    def test_ipv6_loopback(self, enforcer: NetworkEnforcer):
        assert enforcer.classify_zone("::1") == NetworkZone.LOOPBACK

    def test_127_x_range(self, enforcer: NetworkEnforcer):
        assert enforcer.classify_zone("127.0.1.1") == NetworkZone.LOOPBACK
        assert enforcer.classify_zone("127.255.255.255") == NetworkZone.LOOPBACK

    def test_loopback_outbound_allowed(self, enforcer: NetworkEnforcer):
        assert enforcer.check_outbound("127.0.0.1", 8000) is True

    def test_localhost_outbound_allowed(self, enforcer: NetworkEnforcer):
        assert enforcer.check_outbound("localhost", 11434) is True


# -----------------------------------------------------------------------
# Zone B — Trusted On-Prem Allowlist
# -----------------------------------------------------------------------


class TestZoneBTrustedAllowlist:
    """Zone B allows only explicitly configured hosts."""

    def test_configured_host_classified_as_trusted(
        self, enforcer: NetworkEnforcer
    ):
        assert (
            enforcer.classify_zone("192.168.1.100")
            == NetworkZone.TRUSTED_ONPREM
        )

    def test_configured_host_outbound_allowed(
        self, enforcer: NetworkEnforcer
    ):
        assert enforcer.check_outbound("192.168.1.100", 443) is True

    def test_second_configured_host(self, enforcer: NetworkEnforcer):
        assert (
            enforcer.classify_zone("10.0.0.5") == NetworkZone.TRUSTED_ONPREM
        )

    def test_private_ip_NOT_in_allowlist_is_external(
        self, enforcer: NetworkEnforcer
    ):
        """RFC-1918 addresses are NOT auto-trusted."""
        assert enforcer.classify_zone("192.168.1.200") == NetworkZone.EXTERNAL
        assert enforcer.classify_zone("10.0.0.99") == NetworkZone.EXTERNAL
        assert enforcer.classify_zone("172.16.0.1") == NetworkZone.EXTERNAL

    def test_private_ip_not_in_allowlist_denied(
        self, enforcer: NetworkEnforcer
    ):
        assert enforcer.check_outbound("192.168.1.200", 80) is False

    def test_add_trusted_host_at_runtime(
        self, sov_logger: SovereigntyLogger
    ):
        enf = NetworkEnforcer(sov_logger)
        assert enf.classify_zone("10.0.0.42") == NetworkZone.EXTERNAL

        enf.add_trusted_host("10.0.0.42")
        assert enf.classify_zone("10.0.0.42") == NetworkZone.TRUSTED_ONPREM

    def test_remove_trusted_host(self, sov_logger: SovereigntyLogger):
        enf = NetworkEnforcer(sov_logger, trusted_hosts=["10.0.0.42"])
        assert enf.classify_zone("10.0.0.42") == NetworkZone.TRUSTED_ONPREM

        enf.remove_trusted_host("10.0.0.42")
        assert enf.classify_zone("10.0.0.42") == NetworkZone.EXTERNAL

    def test_trusted_hosts_property(self, enforcer: NetworkEnforcer):
        hosts = enforcer.trusted_hosts
        assert isinstance(hosts, frozenset)
        assert "192.168.1.100" in hosts
        assert "10.0.0.5" in hosts

    def test_empty_allowlist_trusts_nothing(
        self, sov_logger: SovereigntyLogger
    ):
        enf = NetworkEnforcer(sov_logger, trusted_hosts=[])
        assert enf.classify_zone("192.168.1.1") == NetworkZone.EXTERNAL


# -----------------------------------------------------------------------
# Zone C — External (Default Deny)
# -----------------------------------------------------------------------


class TestZoneCExternalDeny:
    """External/internet destinations must be denied by default."""

    def test_public_ip_classified_external(self, enforcer: NetworkEnforcer):
        assert enforcer.classify_zone("8.8.8.8") == NetworkZone.EXTERNAL

    def test_public_domain_classified_external(
        self, enforcer: NetworkEnforcer
    ):
        assert enforcer.classify_zone("google.com") == NetworkZone.EXTERNAL

    def test_cloud_service_classified_external(
        self, enforcer: NetworkEnforcer
    ):
        assert (
            enforcer.classify_zone("api.openai.com") == NetworkZone.EXTERNAL
        )

    def test_external_outbound_denied(self, enforcer: NetworkEnforcer):
        assert enforcer.check_outbound("8.8.8.8", 53) is False

    def test_external_domain_outbound_denied(
        self, enforcer: NetworkEnforcer
    ):
        assert enforcer.check_outbound("google.com", 443) is False

    def test_public_dns_denied(self, enforcer: NetworkEnforcer):
        assert enforcer.check_outbound("1.1.1.1", 53) is False


# -----------------------------------------------------------------------
# Unknown / Invalid Destinations → DENY
# -----------------------------------------------------------------------


class TestUnknownDestinations:
    """Any destination that cannot be classified must default to DENY."""

    def test_random_hostname_classified_external(
        self, enforcer: NetworkEnforcer
    ):
        assert (
            enforcer.classify_zone("totally.made.up.host")
            == NetworkZone.EXTERNAL
        )

    def test_empty_string_classified_external(
        self, enforcer: NetworkEnforcer
    ):
        assert enforcer.classify_zone("") == NetworkZone.EXTERNAL

    def test_random_hostname_denied(self, enforcer: NetworkEnforcer):
        assert enforcer.check_outbound("unknown.example", 9999) is False

    def test_numeric_nonsense_classified_external(
        self, enforcer: NetworkEnforcer
    ):
        assert enforcer.classify_zone("999.999.999.999") == NetworkZone.EXTERNAL


# -----------------------------------------------------------------------
# Blocked-Attempt Logging
# -----------------------------------------------------------------------


class TestBlockedAttemptLogging:
    """Blocked outbound attempts must be observable in the sovereignty log."""

    def test_blocked_attempt_creates_event(
        self,
        enforcer: NetworkEnforcer,
        sov_logger: SovereigntyLogger,
    ):
        enforcer.check_outbound("8.8.8.8", 53, source_component="test")

        events = sov_logger.get_events(
            event_type=SovereigntyEventType.NETWORK_BLOCKED
        )
        assert len(events) == 1
        assert "8.8.8.8" in events[0].detail
        assert events[0].severity == SovereigntyEventSeverity.CRITICAL

    def test_blocked_event_metadata(
        self,
        enforcer: NetworkEnforcer,
        sov_logger: SovereigntyLogger,
    ):
        enforcer.check_outbound("evil.example.com", 443)

        events = sov_logger.get_events(
            event_type=SovereigntyEventType.NETWORK_BLOCKED
        )
        assert len(events) == 1
        meta = events[0].metadata
        assert meta["host"] == "evil.example.com"
        assert meta["port"] == 443
        assert meta["zone"] == "EXTERNAL"

    def test_allowed_attempt_also_logged(
        self,
        enforcer: NetworkEnforcer,
        sov_logger: SovereigntyLogger,
    ):
        enforcer.check_outbound("127.0.0.1", 8000)

        events = sov_logger.get_events(
            event_type=SovereigntyEventType.NETWORK_ALLOWED
        )
        assert len(events) == 1
        assert "127.0.0.1" in events[0].detail

    def test_multiple_blocked_attempts_counted(
        self,
        enforcer: NetworkEnforcer,
        sov_logger: SovereigntyLogger,
    ):
        enforcer.check_outbound("8.8.8.8", 53)
        enforcer.check_outbound("1.1.1.1", 53)
        enforcer.check_outbound("api.openai.com", 443)

        events = sov_logger.get_events(
            event_type=SovereigntyEventType.NETWORK_BLOCKED
        )
        assert len(events) == 3

    def test_summary_reflects_blocked_events(
        self,
        enforcer: NetworkEnforcer,
        sov_logger: SovereigntyLogger,
    ):
        enforcer.check_outbound("8.8.8.8", 53)
        enforcer.check_outbound("127.0.0.1", 8000)

        summary = sov_logger.get_summary()
        assert summary.total_events == 2
        assert summary.counts_by_type["NETWORK_BLOCKED"] == 1
        assert summary.counts_by_type["NETWORK_ALLOWED"] == 1


# -----------------------------------------------------------------------
# DNS Monitor
# -----------------------------------------------------------------------


class TestDNSMonitor:
    """DNS monitoring: block external, allow loopback/trusted."""

    def test_external_dns_blocked(self, dns_monitor: DNSMonitor):
        allowed, resolved = dns_monitor.check_dns_query("google.com")
        assert allowed is False
        assert resolved is None

    def test_external_dns_logs_blocked_event(
        self,
        dns_monitor: DNSMonitor,
        sov_logger: SovereigntyLogger,
    ):
        dns_monitor.check_dns_query("evil.example.com")

        events = sov_logger.get_events(
            event_type=SovereigntyEventType.DNS_BLOCKED
        )
        assert len(events) == 1
        assert "evil.example.com" in events[0].detail

    @patch("app.services.sovereignty.dns_monitor.socket.gethostbyname")
    def test_loopback_dns_allowed(self, mock_resolve, dns_monitor: DNSMonitor):
        mock_resolve.return_value = "127.0.0.1"
        allowed, resolved = dns_monitor.check_dns_query("localhost")
        assert allowed is True
        assert resolved == "127.0.0.1"

    @patch("app.services.sovereignty.dns_monitor.socket.gethostbyname")
    def test_trusted_host_dns_allowed(
        self, mock_resolve, dns_monitor: DNSMonitor
    ):
        mock_resolve.return_value = "192.168.1.100"
        allowed, resolved = dns_monitor.check_dns_query("192.168.1.100")
        assert allowed is True

    @patch("app.services.sovereignty.dns_monitor.socket.gethostbyname")
    def test_allowed_dns_logs_query_event(
        self,
        mock_resolve,
        dns_monitor: DNSMonitor,
        sov_logger: SovereigntyLogger,
    ):
        mock_resolve.return_value = "127.0.0.1"
        dns_monitor.check_dns_query("localhost")

        events = sov_logger.get_events(
            event_type=SovereigntyEventType.DNS_QUERY
        )
        assert len(events) == 1
        assert "localhost" in events[0].detail
