"""Sprint 5 – Audit Event Store Tests.

Tests structured audit event creation, querying, filtering,
and security event retrieval.
"""

import pytest

from app.services.audit import AuditEventStore
from app.schemas.audit import AuditEventType, AuditSeverity


@pytest.fixture
def store():
    return AuditEventStore()


class TestAuditEventCreation:
    """Test audit event recording."""

    def test_record_creates_event(self, store):
        """Recording must create an event with all fields."""
        event = store.record(
            AuditEventType.TASK_CREATED,
            detail="Test task created",
            task_id="task-1",
        )
        assert event.event_type == AuditEventType.TASK_CREATED
        assert event.detail == "Test task created"
        assert event.task_id == "task-1"
        assert event.event_id.startswith("evt-")

    def test_record_with_actor(self, store):
        """Events can specify an actor and role."""
        event = store.record(
            AuditEventType.APPROVAL_DECIDED,
            detail="Approved",
            actor="user-1",
            actor_role="APPROVER",
            task_id="task-2",
        )
        assert event.actor == "user-1"
        assert str(event.actor_role) == "APPROVER"

    def test_record_with_severity(self, store):
        """Events can specify severity levels."""
        event = store.record(
            AuditEventType.SECURITY_VIOLATION,
            detail="Unauthorized access",
            severity=AuditSeverity.CRITICAL,
        )
        assert event.severity == AuditSeverity.CRITICAL

    def test_record_with_metadata(self, store):
        """Events can carry structured metadata."""
        event = store.record(
            AuditEventType.TOOL_CALLED,
            detail="calculate tool invoked",
            metadata={"tool_name": "calculate", "expression": "2+2"},
        )
        assert event.metadata["tool_name"] == "calculate"

    def test_event_has_timestamp(self, store):
        """Every event must have a timestamp."""
        event = store.record(AuditEventType.TASK_CREATED, detail="test")
        assert event.timestamp is not None
        assert len(event.timestamp) > 0


class TestAuditEventQuerying:
    """Test audit event retrieval and filtering."""

    def test_list_events_returns_all(self, store):
        """list_events() returns all events by default."""
        store.record(AuditEventType.TASK_CREATED, detail="one")
        store.record(AuditEventType.TASK_COMPLETED, detail="two")
        events = store.list_events()
        assert len(events) == 2

    def test_list_events_most_recent_first(self, store):
        """Events are returned most recent first."""
        store.record(AuditEventType.TASK_CREATED, detail="first")
        store.record(AuditEventType.TASK_COMPLETED, detail="second")
        events = store.list_events()
        assert events[0].detail == "second"

    def test_filter_by_event_type(self, store):
        """Can filter events by type."""
        store.record(AuditEventType.TASK_CREATED, detail="create")
        store.record(AuditEventType.TOOL_CALLED, detail="tool")
        store.record(AuditEventType.TASK_CREATED, detail="another create")
        events = store.list_events(event_type=AuditEventType.TASK_CREATED)
        assert len(events) == 2

    def test_filter_by_task_id(self, store):
        """Can filter events by task ID."""
        store.record(AuditEventType.TASK_CREATED, detail="t1", task_id="task-1")
        store.record(AuditEventType.TASK_CREATED, detail="t2", task_id="task-2")
        events = store.list_events(task_id="task-1")
        assert len(events) == 1
        assert events[0].task_id == "task-1"

    def test_filter_by_severity(self, store):
        """Can filter events by severity."""
        store.record(AuditEventType.TASK_CREATED, detail="info")
        store.record(
            AuditEventType.SECURITY_VIOLATION,
            detail="critical",
            severity=AuditSeverity.CRITICAL,
        )
        events = store.list_events(severity=AuditSeverity.CRITICAL)
        assert len(events) == 1
        assert events[0].severity == AuditSeverity.CRITICAL

    def test_limit_results(self, store):
        """Can limit the number of returned events."""
        for i in range(20):
            store.record(AuditEventType.TASK_CREATED, detail=f"event-{i}")
        events = store.list_events(limit=5)
        assert len(events) == 5

    def test_get_event_by_id(self, store):
        """Can retrieve a specific event by ID."""
        event = store.record(AuditEventType.TASK_CREATED, detail="find me")
        found = store.get_event(event.event_id)
        assert found is not None
        assert found.detail == "find me"

    def test_get_nonexistent_event(self, store):
        """Returns None for nonexistent event ID."""
        assert store.get_event("nonexistent") is None


class TestSecurityEvents:
    """Test security event retrieval."""

    def test_get_security_events(self, store):
        """get_security_events() returns only security-related events."""
        store.record(AuditEventType.TASK_CREATED, detail="normal")
        store.record(AuditEventType.TOOL_BLOCKED, detail="blocked")
        store.record(AuditEventType.SECURITY_VIOLATION, detail="violation")
        store.record(AuditEventType.PROMPT_INJECTION_DETECTED, detail="injection")
        store.record(AuditEventType.SOVEREIGNTY_BLOCKED, detail="sovereignty")
        store.record(AuditEventType.TASK_COMPLETED, detail="normal2")

        security = store.get_security_events()
        assert len(security) == 4

    def test_count_by_type(self, store):
        """count_by_type() returns correct counts."""
        store.record(AuditEventType.TOOL_CALLED, detail="one")
        store.record(AuditEventType.TOOL_CALLED, detail="two")
        store.record(AuditEventType.TOOL_BLOCKED, detail="blocked")
        assert store.count_by_type(AuditEventType.TOOL_CALLED) == 2
        assert store.count_by_type(AuditEventType.TOOL_BLOCKED) == 1

    def test_total_events(self, store):
        """total_events property returns correct total."""
        assert store.total_events == 0
        store.record(AuditEventType.TASK_CREATED, detail="test")
        assert store.total_events == 1
