"""Sprint 5 – Tests for the Sovereignty Logger.

Covers:
  - SovereigntyEvent model creation and field defaults
  - SovereigntyLogger ring buffer capacity enforcement
  - Event emission and retrieval
  - Filtering by event type, severity, and time range
  - Summary / aggregation
  - Thread safety (basic concurrent writes)
  - Clear / housekeeping
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest

from app.services.sovereignty.sovereignty_logger import (
    SovereigntyEvent,
    SovereigntyEventSummary,
    SovereigntyLogger,
)
from shared.enums import SovereigntyEventSeverity, SovereigntyEventType


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def sov_logger() -> SovereigntyLogger:
    """Fresh sovereignty logger with small buffer for testing."""
    return SovereigntyLogger(max_events=50)


# -----------------------------------------------------------------------
# SovereigntyEvent model tests
# -----------------------------------------------------------------------


class TestSovereigntyEventModel:
    """Verify the SovereigntyEvent Pydantic model."""

    def test_event_has_auto_generated_id(self):
        event = SovereigntyEvent(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
        )
        assert event.event_id.startswith("sev-")
        assert len(event.event_id) == 16  # "sev-" + 12 hex chars

    def test_event_has_utc_timestamp(self):
        event = SovereigntyEvent(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
        )
        # ISO-8601 UTC string should contain timezone info
        assert "T" in event.timestamp
        # Parseable
        parsed = datetime.fromisoformat(event.timestamp)
        assert parsed.tzinfo is not None

    def test_event_defaults(self):
        event = SovereigntyEvent(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
        )
        assert event.severity == SovereigntyEventSeverity.INFO
        assert event.detail == ""
        assert event.metadata == {}

    def test_event_with_all_fields(self):
        event = SovereigntyEvent(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            severity=SovereigntyEventSeverity.CRITICAL,
            source_component="network_enforcer",
            detail="Blocked outbound to 8.8.8.8:53",
            metadata={"dest_ip": "8.8.8.8", "dest_port": 53},
        )
        assert event.event_type == SovereigntyEventType.NETWORK_BLOCKED
        assert event.severity == SovereigntyEventSeverity.CRITICAL
        assert event.source_component == "network_enforcer"
        assert event.detail == "Blocked outbound to 8.8.8.8:53"
        assert event.metadata["dest_ip"] == "8.8.8.8"


# -----------------------------------------------------------------------
# SovereigntyLogger core tests
# -----------------------------------------------------------------------


class TestLogEvent:
    """Verify basic event logging."""

    def test_log_event_returns_event(self, sov_logger: SovereigntyLogger):
        event = sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="main",
            detail="Backend started",
        )
        assert isinstance(event, SovereigntyEvent)
        assert event.event_type == SovereigntyEventType.STARTUP

    def test_log_event_stores_event(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="main",
        )
        assert sov_logger.event_count == 1

    def test_log_multiple_events(self, sov_logger: SovereigntyLogger):
        for i in range(5):
            sov_logger.log_event(
                event_type=SovereigntyEventType.NETWORK_ALLOWED,
                source_component="network",
                detail=f"Connection {i}",
            )
        assert sov_logger.event_count == 5

    def test_log_event_with_metadata(self, sov_logger: SovereigntyLogger):
        event = sov_logger.log_event(
            event_type=SovereigntyEventType.DNS_QUERY,
            source_component="dns_monitor",
            metadata={"hostname": "localhost", "resolved": "127.0.0.1"},
        )
        assert event.metadata["hostname"] == "localhost"


# -----------------------------------------------------------------------
# Ring buffer capacity tests
# -----------------------------------------------------------------------


class TestRingBuffer:
    """Verify ring buffer eviction and capacity enforcement."""

    def test_buffer_respects_max_capacity(self):
        small_logger = SovereigntyLogger(max_events=5)
        for i in range(10):
            small_logger.log_event(
                event_type=SovereigntyEventType.NETWORK_ALLOWED,
                source_component="test",
                detail=f"Event {i}",
            )
        # Only last 5 retained
        assert small_logger.event_count == 5

    def test_oldest_events_evicted_first(self):
        small_logger = SovereigntyLogger(max_events=3)
        for i in range(5):
            small_logger.log_event(
                event_type=SovereigntyEventType.NETWORK_ALLOWED,
                source_component="test",
                detail=f"Event {i}",
            )
        events = small_logger.get_events()
        # Most recent first: Event 4, Event 3, Event 2
        assert events[0].detail == "Event 4"
        assert events[1].detail == "Event 3"
        assert events[2].detail == "Event 2"
        assert len(events) == 3

    def test_default_capacity(self):
        default_logger = SovereigntyLogger()
        assert default_logger.event_count == 0
        # Should accept many events without error
        for i in range(100):
            default_logger.log_event(
                event_type=SovereigntyEventType.STARTUP,
                source_component="test",
            )
        assert default_logger.event_count == 100


# -----------------------------------------------------------------------
# Filtering tests
# -----------------------------------------------------------------------


class TestFiltering:
    """Verify event filtering by type, severity, and time."""

    def test_filter_by_event_type(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="main",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            source_component="enforcer",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="main",
        )

        startup_events = sov_logger.get_events(
            event_type=SovereigntyEventType.STARTUP
        )
        assert len(startup_events) == 2
        assert all(
            e.event_type == SovereigntyEventType.STARTUP
            for e in startup_events
        )

    def test_filter_by_severity(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_ALLOWED,
            severity=SovereigntyEventSeverity.INFO,
            source_component="test",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            severity=SovereigntyEventSeverity.CRITICAL,
            source_component="test",
        )

        critical = sov_logger.get_events(
            severity=SovereigntyEventSeverity.CRITICAL
        )
        assert len(critical) == 1
        assert critical[0].event_type == SovereigntyEventType.NETWORK_BLOCKED

    def test_filter_by_since(self, sov_logger: SovereigntyLogger):
        # Log an event and note the time boundary
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
            detail="early",
        )
        boundary = datetime.now(timezone.utc).isoformat()
        sov_logger.log_event(
            event_type=SovereigntyEventType.SHUTDOWN,
            source_component="test",
            detail="late",
        )

        recent = sov_logger.get_events(since=boundary)
        assert len(recent) >= 1
        assert all(e.detail == "late" for e in recent)

    def test_filter_with_limit(self, sov_logger: SovereigntyLogger):
        for i in range(10):
            sov_logger.log_event(
                event_type=SovereigntyEventType.NETWORK_ALLOWED,
                source_component="test",
                detail=f"Event {i}",
            )
        limited = sov_logger.get_events(limit=3)
        assert len(limited) == 3
        # Most recent first
        assert limited[0].detail == "Event 9"

    def test_combined_filters(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            severity=SovereigntyEventSeverity.CRITICAL,
            source_component="enforcer",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            severity=SovereigntyEventSeverity.WARNING,
            source_component="enforcer",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.TOOL_BLOCKED,
            severity=SovereigntyEventSeverity.CRITICAL,
            source_component="tool_guard",
        )

        result = sov_logger.get_events(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            severity=SovereigntyEventSeverity.CRITICAL,
        )
        assert len(result) == 1

    def test_filter_returns_empty_when_no_match(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
        )
        result = sov_logger.get_events(
            event_type=SovereigntyEventType.SANDBOX_ESCAPE_ATTEMPT
        )
        assert result == []

    def test_get_events_returns_most_recent_first(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
            detail="first",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.SHUTDOWN,
            source_component="test",
            detail="second",
        )
        events = sov_logger.get_events()
        assert events[0].detail == "second"
        assert events[1].detail == "first"


# -----------------------------------------------------------------------
# get_latest tests
# -----------------------------------------------------------------------


class TestGetLatest:

    def test_latest_on_empty_logger(self, sov_logger: SovereigntyLogger):
        assert sov_logger.get_latest() is None

    def test_latest_returns_most_recent(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
            detail="first",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.SHUTDOWN,
            source_component="test",
            detail="second",
        )
        latest = sov_logger.get_latest()
        assert latest is not None
        assert latest.detail == "second"


# -----------------------------------------------------------------------
# Summary / aggregation tests
# -----------------------------------------------------------------------


class TestSummary:
    """Verify summary aggregation."""

    def test_empty_summary(self, sov_logger: SovereigntyLogger):
        summary = sov_logger.get_summary()
        assert summary.total_events == 0
        assert summary.counts_by_type == {}
        assert summary.counts_by_severity == {}
        assert summary.latest_event is None
        assert summary.critical_count == 0
        assert summary.warning_count == 0

    def test_summary_counts_by_type(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            source_component="enforcer",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            source_component="enforcer",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.DNS_QUERY,
            source_component="dns_monitor",
        )

        summary = sov_logger.get_summary()
        assert summary.total_events == 3
        assert summary.counts_by_type["NETWORK_BLOCKED"] == 2
        assert summary.counts_by_type["DNS_QUERY"] == 1

    def test_summary_counts_by_severity(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_ALLOWED,
            severity=SovereigntyEventSeverity.INFO,
            source_component="test",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.ZONE_VIOLATION,
            severity=SovereigntyEventSeverity.WARNING,
            source_component="test",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.NETWORK_BLOCKED,
            severity=SovereigntyEventSeverity.CRITICAL,
            source_component="test",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.SANDBOX_ESCAPE_ATTEMPT,
            severity=SovereigntyEventSeverity.CRITICAL,
            source_component="test",
        )

        summary = sov_logger.get_summary()
        assert summary.counts_by_severity["INFO"] == 1
        assert summary.counts_by_severity["WARNING"] == 1
        assert summary.counts_by_severity["CRITICAL"] == 2
        assert summary.critical_count == 2
        assert summary.warning_count == 1

    def test_summary_includes_latest_event(self, sov_logger: SovereigntyLogger):
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
            detail="first",
        )
        sov_logger.log_event(
            event_type=SovereigntyEventType.SHUTDOWN,
            source_component="test",
            detail="last",
        )
        summary = sov_logger.get_summary()
        assert summary.latest_event is not None
        assert summary.latest_event.detail == "last"


# -----------------------------------------------------------------------
# Housekeeping tests
# -----------------------------------------------------------------------


class TestHousekeeping:

    def test_clear_removes_all_events(self, sov_logger: SovereigntyLogger):
        for _ in range(5):
            sov_logger.log_event(
                event_type=SovereigntyEventType.STARTUP,
                source_component="test",
            )
        assert sov_logger.event_count == 5
        sov_logger.clear()
        assert sov_logger.event_count == 0
        assert sov_logger.get_events() == []

    def test_event_count_property(self, sov_logger: SovereigntyLogger):
        assert sov_logger.event_count == 0
        sov_logger.log_event(
            event_type=SovereigntyEventType.STARTUP,
            source_component="test",
        )
        assert sov_logger.event_count == 1


# -----------------------------------------------------------------------
# Thread safety (basic smoke test)
# -----------------------------------------------------------------------


class TestThreadSafety:

    def test_concurrent_writes(self):
        """Verify no crashes or data corruption under concurrent logging."""
        sov_logger = SovereigntyLogger(max_events=500)
        barrier = threading.Barrier(4)

        def writer(thread_id: int):
            barrier.wait()
            for i in range(100):
                sov_logger.log_event(
                    event_type=SovereigntyEventType.NETWORK_ALLOWED,
                    source_component=f"thread-{thread_id}",
                    detail=f"Event {i}",
                )

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 4 threads × 100 events = 400, all fit within max_events=500
        assert sov_logger.event_count == 400

    def test_concurrent_writes_with_eviction(self):
        """Verify ring buffer eviction under concurrent logging."""
        sov_logger = SovereigntyLogger(max_events=50)
        barrier = threading.Barrier(4)

        def writer(thread_id: int):
            barrier.wait()
            for i in range(100):
                sov_logger.log_event(
                    event_type=SovereigntyEventType.NETWORK_ALLOWED,
                    source_component=f"thread-{thread_id}",
                    detail=f"Event {i}",
                )

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 400 total written, but max_events=50 → exactly 50 retained
        assert sov_logger.event_count == 50
