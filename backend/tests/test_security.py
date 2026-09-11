"""Sprint 5 – Security & Policy Enforcement Tests.

Tests:
  1. Tool permission enforcement (role-based blocking)
  2. Document trust boundary (untrusted tagging)
  3. Prompt-injection detection
  4. validate_artifact tool correctness
"""

import pytest

from app.services.audit import AuditEventStore
from app.schemas.audit import AuditEventType
from shared.enums import UserRole


class TestToolPermissionEnforcement:
    """Test that tool execution respects required_role."""

    def test_engineer_can_use_engineer_tools(self):
        """ENGINEER role can use tools requiring ENGINEER."""
        from app.services.agent.loop import _ROLE_HIERARCHY, AgentLoop
        user_level = _ROLE_HIERARCHY[UserRole.ENGINEER]
        required_level = _ROLE_HIERARCHY[UserRole.ENGINEER]
        assert user_level >= required_level

    def test_approver_can_use_engineer_tools(self):
        """APPROVER role can use tools requiring ENGINEER (higher privilege)."""
        from app.services.agent.loop import _ROLE_HIERARCHY
        assert _ROLE_HIERARCHY[UserRole.APPROVER] >= _ROLE_HIERARCHY[UserRole.ENGINEER]

    def test_engineer_cannot_use_admin_tools(self):
        """ENGINEER role cannot use tools requiring ADMIN."""
        from app.services.agent.loop import _ROLE_HIERARCHY
        assert _ROLE_HIERARCHY[UserRole.ENGINEER] < _ROLE_HIERARCHY[UserRole.ADMIN]

    def test_admin_outranks_all(self):
        """ADMIN role outranks all other roles."""
        from app.services.agent.loop import _ROLE_HIERARCHY
        admin_level = _ROLE_HIERARCHY[UserRole.ADMIN]
        for role, level in _ROLE_HIERARCHY.items():
            assert admin_level >= level

    def test_tool_blocked_recorded_in_audit(self):
        """Blocked tool calls must be recorded in audit store."""
        from app.services.agent.loop import AgentLoop
        audit_store = AuditEventStore()

        # Create a minimal AgentLoop to test _record_tool_blocked
        # We can't run the full loop without a model adapter, but we
        # can test the recording mechanism directly.
        class FakeAdapter:
            pass
        from app.services.tools.registry import ToolRegistry
        loop = AgentLoop(
            task_id="test-blocked",
            adapter=FakeAdapter(),
            registry=ToolRegistry(),
            user_role=UserRole.ENGINEER,
            audit_store=audit_store,
        )

        loop._record_tool_blocked("admin_tool", UserRole.ADMIN)

        events = audit_store.list_events(event_type=AuditEventType.TOOL_BLOCKED)
        assert len(events) == 1
        assert "admin_tool" in events[0].detail
        assert "ENGINEER" in events[0].detail

    def test_tool_called_recorded_in_audit(self):
        """Successful tool calls must be recorded in audit store."""
        from app.services.agent.loop import AgentLoop
        audit_store = AuditEventStore()

        class FakeAdapter:
            pass
        from app.services.tools.registry import ToolRegistry
        loop = AgentLoop(
            task_id="test-called",
            adapter=FakeAdapter(),
            registry=ToolRegistry(),
            user_role=UserRole.ENGINEER,
            audit_store=audit_store,
        )

        loop._record_tool_called("calculate")

        events = audit_store.list_events(event_type=AuditEventType.TOOL_CALLED)
        assert len(events) == 1
        assert "calculate" in events[0].detail

    def test_permission_check_method(self):
        """_check_tool_permission correctly evaluates role hierarchy."""
        from app.services.agent.loop import AgentLoop
        from app.services.tools.registry import ToolRegistry

        class FakeAdapter:
            pass

        # ENGINEER trying to use APPROVER tool
        loop = AgentLoop(
            task_id="test-perm",
            adapter=FakeAdapter(),
            registry=ToolRegistry(),
            user_role=UserRole.ENGINEER,
        )
        assert loop._check_tool_permission("tool", UserRole.ENGINEER) is True
        assert loop._check_tool_permission("tool", UserRole.APPROVER) is False
        assert loop._check_tool_permission("tool", UserRole.ADMIN) is False

        # ADMIN trying to use any tool
        loop_admin = AgentLoop(
            task_id="test-perm-admin",
            adapter=FakeAdapter(),
            registry=ToolRegistry(),
            user_role=UserRole.ADMIN,
        )
        assert loop_admin._check_tool_permission("tool", UserRole.ENGINEER) is True
        assert loop_admin._check_tool_permission("tool", UserRole.APPROVER) is True
        assert loop_admin._check_tool_permission("tool", UserRole.ADMIN) is True


class TestDocumentTrustBoundary:
    """Test that document-extracted evidence is tagged as untrusted."""

    @pytest.fixture
    def parser(self):
        from app.services.document_parser import DocumentParser
        return DocumentParser()

    def test_evidence_tagged_as_untrusted(self, parser):
        """All evidence objects must have trust_level: untrusted."""
        import asyncio
        response = asyncio.run(parser.parse_document(
            document_id="doc-trust-test",
            content=b"test document content",
        ))
        for ev in response.evidence_objects:
            assert ev.metadata.get("trust_level") == "untrusted", (
                f"Evidence {ev.evidence_id} missing untrusted tag"
            )

    def test_evidence_has_trust_boundary_tag(self, parser):
        """All evidence objects must have trust_boundary: document_extract."""
        import asyncio
        response = asyncio.run(parser.parse_document(
            document_id="doc-boundary-test",
            content=b"test content",
        ))
        for ev in response.evidence_objects:
            assert ev.metadata.get("trust_boundary") == "document_extract"


class TestPromptInjectionDetection:
    """Test prompt-injection pattern detection in documents."""

    @pytest.fixture
    def parser(self):
        from app.services.document_parser import DocumentParser
        return DocumentParser()

    def test_injection_patterns_exist(self):
        """The injection pattern list must be non-empty."""
        from app.services.document_parser import _INJECTION_PATTERNS
        assert len(_INJECTION_PATTERNS) > 0

    def test_clean_document_no_injection(self, parser):
        """Clean documents should not trigger injection detection."""
        import asyncio
        response = asyncio.run(parser.parse_document(
            document_id="doc-clean",
            content=b"Normal inspection report content",
        ))
        for ev in response.evidence_objects:
            assert ev.metadata.get("injection_detected") is not True


class TestValidateArtifactTool:
    """Test the fixed validate_artifact tool implementation."""

    def test_valid_docx_type(self):
        """DOCX type should be recognized as structurally valid."""
        from app.services.tools.implementations import validate_artifact
        result = validate_artifact("DOCX", "Evidence report with verification results")
        assert result["structural_valid"] is True

    def test_valid_xlsx_type(self):
        """XLSX type should be recognized as structurally valid."""
        from app.services.tools.implementations import validate_artifact
        result = validate_artifact("XLSX", "Calculation results for inspection compliance")
        assert result["structural_valid"] is True

    def test_valid_pdf_type(self):
        """PDF type should be recognized as structurally valid."""
        from app.services.tools.implementations import validate_artifact
        result = validate_artifact("PDF", "Evidence report with compliance verification")
        assert result["structural_valid"] is True

    def test_unsupported_type_fails(self):
        """Unsupported artifact types must fail validation."""
        from app.services.tools.implementations import validate_artifact
        result = validate_artifact("ZIP", "Some content")
        assert result["structural_valid"] is False

    def test_semantic_requires_keywords(self):
        """Semantic validation requires domain-relevant keywords."""
        from app.services.tools.implementations import validate_artifact
        # Missing domain keywords
        result = validate_artifact("DOCX", "Hello world")
        assert result["semantic_valid"] is False

    def test_semantic_passes_with_keywords(self):
        """Semantic validation passes with domain-relevant content."""
        from app.services.tools.implementations import validate_artifact
        result = validate_artifact("DOCX", "Evidence report with verification results")
        assert result["semantic_valid"] is True

    def test_empty_content_fails_semantic(self):
        """Empty content summary must fail semantic validation."""
        from app.services.tools.implementations import validate_artifact
        result = validate_artifact("DOCX", "")
        assert result["semantic_valid"] is False
