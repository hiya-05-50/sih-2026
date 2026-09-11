"""Sprint 4 – Flagship Pipeline Tests.

Tests:
  - End-to-end V3 slice produces all 3 artifacts
  - Pipeline stages are tracked
  - Full traceability from evidence → artifact
  - Verification report contains all 8 checks
"""

import asyncio
import pytest
from app.services.flagship_pipeline import FlagshipPipeline
from app.services.approval import ApprovalService
from app.adapters.manager import AdapterManager
from app.services.registry import ModelRegistry
from app.services.seed import seed_models
from shared.enums import RiskLevel


def _run(coro):
    """Helper to run async coroutines in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def pipeline():
    registry = ModelRegistry()
    _run(seed_models(registry))
    adapter_manager = AdapterManager(registry)
    approval_service = ApprovalService()
    return FlagshipPipeline(adapter_manager, approval_service)


def test_full_flagship_produces_artifacts(pipeline):
    """The full flagship task produces Decision_Note.docx + Inspection_Data.xlsx + Evidence_Report.pdf."""
    result = _run(pipeline.execute())

    assert result.task_id is not None
    assert result.evidence_count > 0
    assert len(result.calculations) > 0
    assert result.verification_report is not None

    # GREEN risk → artifacts should be generated
    if result.risk_level == RiskLevel.GREEN:
        assert result.artifact_manifest is not None
        filenames = {a.filename for a in result.artifact_manifest.artifacts}
        assert "Decision_Note.docx" in filenames
        assert "Inspection_Data.xlsx" in filenames
        assert "Evidence_Report.pdf" in filenames


def test_pipeline_tracks_all_stages(pipeline):
    """Pipeline states should include all 10 stages."""
    result = _run(pipeline.execute())

    expected_stages = [
        "UPLOAD", "OCR_VISION", "EVIDENCE", "RETRIEVAL",
        "REASONING", "DETERMINISTIC_COMPUTE", "VERIFICATION",
        "RISK", "APPROVAL", "ARTIFACT",
    ]
    for stage in expected_stages:
        assert stage in result.pipeline_states, f"Missing stage: {stage}"


def test_calculations_have_provenance(pipeline):
    """Every calculation must have evidence references."""
    result = _run(pipeline.execute())

    for calc in result.calculations:
        assert calc.evidence_reference is not None
        assert calc.evidence_reference.startswith("ev-")
        assert calc.results_match is True  # Deterministic → always matches


def test_verification_report_has_8_checks(pipeline):
    """Verification report must contain all 8 checks."""
    result = _run(pipeline.execute())

    assert result.verification_report is not None
    assert len(result.verification_report.checks) == 8


def test_pipeline_duration_tracked(pipeline):
    """Pipeline duration should be recorded."""
    result = _run(pipeline.execute())
    assert result.pipeline_duration_ms > 0


def test_execution_retrievable(pipeline):
    """Executed pipelines should be retrievable by task ID."""
    result = _run(pipeline.execute())
    retrieved = pipeline.get_execution(result.task_id)
    assert retrieved is not None
    assert retrieved.task_id == result.task_id


def test_artifact_evidence_traceability(pipeline):
    """Artifacts should reference evidence IDs for traceability."""
    result = _run(pipeline.execute())

    if result.artifact_manifest:
        for artifact in result.artifact_manifest.artifacts:
            assert len(artifact.evidence_references) > 0
