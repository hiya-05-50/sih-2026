"""Sprint 6 – Integration Tests.

End-to-end tests for the final integrated SAFIRE system:
  - Full flagship pipeline with routing, audit, sovereignty
  - Security demo (prompt injection containment)
  - Conflicting evidence detection
  - Approval enforcement
  - Artifact validation
  - Demo endpoints
  - Version check
  - Regression safety
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------------
# FLAGSHIP END-TO-END
# -----------------------------------------------------------------------

class TestFlagshipEndToEnd:
    """Test the complete flagship pipeline produces a fully-traced result."""

    def test_flagship_execute_returns_200(self, client):
        resp = client.post("/v1/flagship/execute?user_role=ENGINEER")
        assert resp.status_code == 200

    def test_flagship_has_all_stages(self, client):
        resp = client.post("/v1/flagship/execute?user_role=ENGINEER")
        data = resp.json()
        states = data["pipeline_states"]
        required = [
            "UPLOAD", "CLASSIFY", "OCR_VISION", "EVIDENCE",
            "CONFLICT_CHECK", "RETRIEVAL", "ROUTING", "REASONING",
            "DETERMINISTIC_COMPUTE", "VERIFICATION", "RISK",
            "APPROVAL", "ARTIFACT", "SOVEREIGNTY", "AUDIT",
        ]
        for stage in required:
            assert stage in states, f"Missing pipeline stage: {stage}"

    def test_flagship_has_routing_decision(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert data["routing_decision"] is not None
        rd = data["routing_decision"]
        assert rd["selected_model_name"] != ""
        assert rd["routing_rationale"] != ""
        assert rd["candidates_evaluated"] > 0

    def test_flagship_has_sovereignty_snapshot(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert data["sovereignty_snapshot"] is not None
        ss = data["sovereignty_snapshot"]
        assert ss["state"] in ("READY", "NOT_READY", "DEGRADED")

    def test_flagship_has_verification_report(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert data["verification_report"] is not None
        vr = data["verification_report"]
        assert len(vr["checks"]) == 8  # All 8 verification checks

    def test_flagship_has_audit_trail(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert len(data["audit_event_ids"]) >= 3  # At least UPLOAD, ROUTING, VERIFICATION

    def test_flagship_has_evidence(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert data["evidence_count"] >= 5

    def test_flagship_has_calculations(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert len(data["calculations"]) > 0

    def test_flagship_timing(self, client):
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        assert data["pipeline_duration_ms"] >= 0

    def test_flagship_green_produces_artifacts(self, client):
        """GREEN risk should produce artifact manifest."""
        resp = client.post("/v1/flagship/execute")
        data = resp.json()
        if data["risk_level"] == "GREEN":
            assert data["artifact_manifest"] is not None
            assert data["delivery_blocked"] is False

    def test_flagship_list(self, client):
        client.post("/v1/flagship/execute")
        resp = client.get("/v1/flagship/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# -----------------------------------------------------------------------
# SECURITY DEMO
# -----------------------------------------------------------------------

class TestSecurityDemo:
    """Test the security/prompt-injection demo."""

    def test_security_demo_runs(self, client):
        resp = client.post("/v1/demo/security")
        assert resp.status_code == 200

    def test_all_evidence_untrusted(self, client):
        resp = client.post("/v1/demo/security")
        data = resp.json()
        assert data["all_evidence_untrusted"] is True

    def test_injection_detected(self, client):
        resp = client.post("/v1/demo/security")
        data = resp.json()
        assert data["injection_detected"] is True

    def test_tool_permissions_unchanged(self, client):
        resp = client.post("/v1/demo/security")
        data = resp.json()
        assert data["tool_permissions_unchanged"] is True

    def test_security_events_logged(self, client):
        resp = client.post("/v1/demo/security")
        data = resp.json()
        assert data["security_events_logged"] is True

    def test_legitimate_workflow_continues(self, client):
        resp = client.post("/v1/demo/security")
        data = resp.json()
        assert data["legitimate_workflow_continues"] is True


# -----------------------------------------------------------------------
# CONFLICTING EVIDENCE
# -----------------------------------------------------------------------

class TestConflictingEvidence:
    """Test conflicting evidence surfacing."""

    def test_conflict_demo_runs(self, client):
        resp = client.post("/v1/demo/conflicts")
        assert resp.status_code == 200

    def test_conflicts_detected(self, client):
        resp = client.post("/v1/demo/conflicts")
        data = resp.json()
        assert data["conflicts_detected"] >= 1

    def test_not_silently_averaged(self, client):
        resp = client.post("/v1/demo/conflicts")
        data = resp.json()
        assert data["silently_averaged"] is False

    def test_conflict_has_details(self, client):
        resp = client.post("/v1/demo/conflicts")
        data = resp.json()
        if data["conflicts_detected"] > 0:
            c = data["conflicts"][0]
            assert "parameter" in c
            assert "severity" in c
            assert c["severity"] in ("WARNING", "CRITICAL")


# -----------------------------------------------------------------------
# CODING AGENT DEMO
# -----------------------------------------------------------------------

class TestCodingAgentDemo:
    """Test coding agent workflow structure."""

    def test_coding_demo_runs(self, client):
        resp = client.post("/v1/demo/coding-agent")
        assert resp.status_code == 200

    def test_workflow_has_all_steps(self, client):
        resp = client.post("/v1/demo/coding-agent")
        data = resp.json()
        steps = [s["name"] for s in data["workflow_steps"]]
        required = ["TASK", "MODEL_SELECTION", "CODE_GENERATION",
                     "SANDBOX_EXECUTION", "VERIFICATION"]
        for step in required:
            assert step in steps

    def test_honest_capability_reporting(self, client):
        resp = client.post("/v1/demo/coding-agent")
        data = resp.json()
        # Must honestly report availability
        assert "model_available" in data
        assert "sandbox_available" in data


# -----------------------------------------------------------------------
# MULTIMODAL DEMO
# -----------------------------------------------------------------------

class TestMultimodalDemo:
    """Test multimodal capability reporting."""

    def test_multimodal_demo_runs(self, client):
        resp = client.post("/v1/demo/multimodal")
        assert resp.status_code == 200

    def test_document_parsing_implemented(self, client):
        resp = client.post("/v1/demo/multimodal")
        data = resp.json()
        assert data["capabilities"]["document_parsing"]["status"] == "IMPLEMENTED"

    def test_ocr_implemented(self, client):
        resp = client.post("/v1/demo/multimodal")
        data = resp.json()
        assert data["capabilities"]["ocr"]["status"] == "IMPLEMENTED"


# -----------------------------------------------------------------------
# APPROVAL ENFORCEMENT
# -----------------------------------------------------------------------

class TestApprovalEnforcement:
    """Test backend-enforced approval invariant."""

    def test_engineer_cannot_approve(self, client):
        """ENGINEER role must be denied approval."""
        # Create a pending approval
        client.post("/v1/flagship/execute?user_role=ENGINEER")
        # Find a task with pending approval
        execs = client.get("/v1/flagship/").json()
        pending = [e for e in execs if e.get("approval") and e["approval"]["status"] == "PENDING"]
        if not pending:
            pytest.skip("No pending approvals to test")
        task_id = pending[0]["task_id"]
        # Engineer tries to approve
        resp = client.post(f"/v1/approval/{task_id}/decide", json={
            "user_id": "eng-001",
            "user_role": "ENGINEER",
            "action": "APPROVED",
            "reason": "trying to approve",
        })
        assert resp.status_code == 403

    def test_approver_can_approve(self, client):
        """APPROVER role must be allowed to approve."""
        execs = client.get("/v1/flagship/").json()
        pending = [e for e in execs if e.get("approval") and e["approval"]["status"] == "PENDING"]
        if not pending:
            pytest.skip("No pending approvals to test")
        task_id = pending[0]["task_id"]
        resp = client.post(f"/v1/approval/{task_id}/decide", json={
            "user_id": "approver-001",
            "user_role": "APPROVER",
            "action": "APPROVED",
            "reason": "approved after review",
        })
        assert resp.status_code == 200


# -----------------------------------------------------------------------
# DEMO STATUS
# -----------------------------------------------------------------------

class TestDemoStatus:
    """Test system readiness endpoint."""

    def test_demo_status_returns_200(self, client):
        resp = client.get("/v1/demo/status")
        assert resp.status_code == 200

    def test_demo_status_has_fields(self, client):
        resp = client.get("/v1/demo/status")
        data = resp.json()
        assert "backend" in data
        assert "sovereignty" in data
        assert "demo_readiness" in data
        assert data["backend"]["status"] == "READY"


# -----------------------------------------------------------------------
# VERSION + REGRESSION
# -----------------------------------------------------------------------

class TestVersionAndRegression:
    """Verify Sprint 6 version and regression safety."""

    def test_version_is_0_6(self, client):
        from app.main import app as _app
        assert _app.version in ("0.6.0", "0.7.0")

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_models_endpoint(self, client):
        resp = client.get("/v1/models/")
        assert resp.status_code == 200

    def test_tasks_endpoint(self, client):
        resp = client.get("/v1/tasks/")
        assert resp.status_code == 200

    def test_audit_endpoint(self, client):
        resp = client.get("/v1/audit/")
        assert resp.status_code == 200

    def test_sovereignty_endpoint(self, client):
        resp = client.get("/v1/sovereignty/status")
        assert resp.status_code == 200

    def test_siab_run(self, client):
        resp = client.post("/v1/siab/run")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["configs"]) == 3

    def test_document_upload(self, client):
        resp = client.post("/v1/documents/upload")
        assert resp.status_code == 200

    def test_vertical_slice(self, client):
        resp = client.post("/v1/documents/test-doc/vertical-slice")
        assert resp.status_code == 200
