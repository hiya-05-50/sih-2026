"""Sprint 7 – Demo Sequence Tests.

Tests for the 21-step automated judge demo sequence runner.
Verifies that:
  - All 21 steps execute without unhandled exceptions
  - The sequence is repeatable (run twice, same step count)
  - Individual steps return structured results
  - The traceability endpoint returns all 13 requirements
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestDemoSequenceAPI:
    """Test the /v1/demo/sequence endpoints."""

    def test_no_results_initially(self, client):
        """GET /v1/demo/sequence/latest before any run must return 404."""
        resp = client.get("/v1/demo/sequence/latest")
        assert resp.status_code == 404

    def test_run_sequence(self, client):
        """POST /v1/demo/sequence/run must return 200 with 21 steps."""
        resp = client.post("/v1/demo/sequence/run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_steps"] == 21
        assert len(data["steps"]) == 21
        assert data["run_id"].startswith("demo-")
        assert data["overall_status"] in ("PASS", "FAIL")

    def test_all_steps_have_structured_results(self, client):
        """Every step must have step_number, step_name, status, and detail."""
        resp = client.post("/v1/demo/sequence/run")
        data = resp.json()
        for step in data["steps"]:
            assert "step_number" in step
            assert "step_name" in step
            assert step["status"] in ("PASS", "FAIL", "SKIP")
            assert isinstance(step["detail"], str)
            assert isinstance(step["duration_ms"], (int, float))

    def test_sequence_repeatable(self, client):
        """Running twice should produce same step count."""
        resp1 = client.post("/v1/demo/sequence/run")
        resp2 = client.post("/v1/demo/sequence/run")
        d1 = resp1.json()
        d2 = resp2.json()
        assert len(d1["steps"]) == len(d2["steps"]) == 21
        # Run IDs should be different
        assert d1["run_id"] != d2["run_id"]

    def test_latest_result_after_run(self, client):
        """GET /v1/demo/sequence/latest after run must return 200."""
        client.post("/v1/demo/sequence/run")
        resp = client.get("/v1/demo/sequence/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_steps"] == 21

    def test_list_results(self, client):
        """GET /v1/demo/sequence/results must list all runs."""
        client.post("/v1/demo/sequence/run")
        resp = client.get("/v1/demo/sequence/results")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_individual_step(self, client):
        """GET /v1/demo/sequence/step/{n} must return a valid step."""
        client.post("/v1/demo/sequence/run")
        resp = client.get("/v1/demo/sequence/step/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["step_number"] == 1
        assert data["step_name"] == "Show Workbench"


class TestTraceabilityAPI:
    """Test the /v1/traceability/signoff endpoint."""

    def test_traceability_signoff(self, client):
        """GET /v1/traceability/signoff must return all 13 requirements."""
        resp = client.get("/v1/traceability/signoff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requirements"] == 13
        assert len(data["requirements"]) == 13
        assert data["overall_status"] in ("COMPLETE", "PARTIAL", "INCOMPLETE")

    def test_all_requirements_have_evidence(self, client):
        """Every requirement must have implementation files and evidence detail."""
        resp = client.get("/v1/traceability/signoff")
        data = resp.json()
        for req in data["requirements"]:
            assert req["requirement_id"].startswith("R")
            assert len(req["description"]) > 0
            assert len(req["implementation_files"]) > 0
            assert len(req["evidence_detail"]) > 0
            assert req["status"] in ("IMPLEMENTED", "PARTIAL", "TO BE VALIDATED")

    def test_traceability_report_ids(self, client):
        """Report must have a valid ID and timestamp."""
        resp = client.get("/v1/traceability/signoff")
        data = resp.json()
        assert data["report_id"].startswith("trace-")
        assert len(data["generated_at"]) > 0
