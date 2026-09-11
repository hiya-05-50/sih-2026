"""Sprint 4 – Verification Fabric Tests.

One test per verification check (8 total), plus aggregate tests.
All 8 must pass per the Sprint 4 acceptance gate.
"""

import pytest
from app.services.verification import VerificationFabric
from app.schemas.decision_package import (
    ApprovalDecision,
    ArtifactRecord,
    CalculationResult,
)
from app.schemas.evidence import EvidenceObject, NormalizedRegion
from shared.enums import (
    ApprovalStatus,
    EvidenceType,
    RiskLevel,
    UserRole,
    VerificationType,
    VerificationOutcome,
)


@pytest.fixture
def fabric():
    return VerificationFabric()


@pytest.fixture
def sample_evidence():
    return [
        EvidenceObject(
            evidence_id="ev-001",
            document_id="doc-1",
            source_hash="hash123",
            page_number=1,
            region=NormalizedRegion(x=0.0, y=0.0, width=1.0, height=1.0),
            extracted_text="Pressure 4.2 Bar inspection compliance test PASS",
            evidence_type=EvidenceType.TABLE,
        ),
        EvidenceObject(
            evidence_id="ev-002",
            document_id="doc-1",
            source_hash="hash123",
            page_number=1,
            region=NormalizedRegion(x=0.0, y=0.5, width=1.0, height=0.5),
            extracted_text="Thermal threshold 62°C compliance verified",
            evidence_type=EvidenceType.KEY_VALUE,
        ),
    ]


@pytest.fixture
def passing_calculations():
    return [
        CalculationResult(
            calc_id="calc-1",
            parameter_name="pressure",
            primary_result=4.2,
            recomputed_result=4.2,
            results_match=True,
            threshold=5.0,
            threshold_met=True,
            status="PASS",
            evidence_reference="ev-001",
            formula_used="measured_pressure",
        ),
    ]


class TestCheckEvidence:
    """Check 1 — Evidence: every claim references a valid EvidenceObject."""

    def test_all_evidence_valid(self, fabric, sample_evidence):
        result = fabric.check_evidence(
            ["ev-001", "ev-002"], sample_evidence, "hash123"
        )
        assert result.check_type == VerificationType.EVIDENCE
        assert result.passed is True

    def test_missing_evidence_fails(self, fabric, sample_evidence):
        result = fabric.check_evidence(
            ["ev-001", "ev-999"], sample_evidence, "hash123"
        )
        assert result.passed is False
        assert "ev-999" in result.detail

    def test_hash_mismatch_fails(self, fabric, sample_evidence):
        result = fabric.check_evidence(
            ["ev-001"], sample_evidence, "wrong_hash"
        )
        assert result.passed is False


class TestCheckRetrieval:
    """Check 2 — Retrieval: retrieved evidence is relevant."""

    def test_relevant_retrieval_passes(self, fabric, sample_evidence):
        result = fabric.check_retrieval("pressure inspection", sample_evidence)
        assert result.check_type == VerificationType.RETRIEVAL
        assert result.passed is True

    def test_no_results_fails(self, fabric):
        result = fabric.check_retrieval("query", [])
        assert result.passed is False


class TestCheckCalculation:
    """Check 3 — Calculation: deterministic recomputation matches."""

    def test_matching_calculations_pass(self, fabric, passing_calculations):
        result = fabric.check_calculation(passing_calculations)
        assert result.check_type == VerificationType.CALCULATION
        assert result.passed is True

    def test_mismatch_fails(self, fabric):
        bad_calc = CalculationResult(
            calc_id="calc-bad",
            parameter_name="bad",
            primary_result=5.0,
            recomputed_result=5.5,
            results_match=False,
            status="FAIL",
            evidence_reference="ev-001",
            formula_used="x",
        )
        result = fabric.check_calculation([bad_calc])
        assert result.passed is False


class TestCheckRule:
    """Check 4 — Rule: business rules / thresholds satisfied."""

    def test_all_thresholds_met(self, fabric, passing_calculations):
        result = fabric.check_rule(passing_calculations)
        assert result.check_type == VerificationType.RULE
        assert result.passed is True

    def test_threshold_violated_fails(self, fabric):
        violation = CalculationResult(
            calc_id="calc-v",
            parameter_name="temperature",
            primary_result=72.0,
            recomputed_result=72.0,
            results_match=True,
            threshold=65.0,
            threshold_met=False,
            status="FAIL",
            evidence_reference="ev-002",
            formula_used="measured_temp",
        )
        result = fabric.check_rule([violation])
        assert result.passed is False
        assert "temperature" in result.detail


class TestCheckSchema:
    """Check 5 — Schema: output conforms to expected structure."""

    def test_valid_schema(self, fabric):
        data = {
            "task_id": "t-1",
            "document_id": "d-1",
            "calculations": [],
            "verification_report": {},
            "risk_level": "GREEN",
        }
        result = fabric.check_schema(data)
        assert result.check_type == VerificationType.SCHEMA
        assert result.passed is True

    def test_missing_fields_fails(self, fabric):
        result = fabric.check_schema({"task_id": "t-1"})
        assert result.passed is False


class TestCheckArtifact:
    """Check 6 — Artifact: files pass structural + semantic validation."""

    def test_valid_artifacts(self, fabric):
        artifacts = [
            ArtifactRecord(
                task_id="t-1",
                filename="Decision_Note.docx",
                artifact_type="DOCX",
                structural_valid=True,
                semantic_valid=True,
            ),
        ]
        result = fabric.check_artifact(artifacts)
        assert result.check_type == VerificationType.ARTIFACT
        assert result.passed is True

    def test_structural_failure(self, fabric):
        artifacts = [
            ArtifactRecord(
                task_id="t-1",
                filename="bad.docx",
                artifact_type="DOCX",
                structural_valid=False,
                semantic_valid=True,
            ),
        ]
        result = fabric.check_artifact(artifacts)
        assert result.passed is False

    def test_no_artifacts_fails(self, fabric):
        result = fabric.check_artifact([])
        assert result.passed is False


class TestCheckPermission:
    """Check 7 — Permission: user has required role."""

    def test_engineer_can_execute(self, fabric):
        result = fabric.check_permission(UserRole.ENGINEER, UserRole.ENGINEER)
        assert result.check_type == VerificationType.PERMISSION
        assert result.passed is True

    def test_approver_meets_engineer(self, fabric):
        result = fabric.check_permission(UserRole.APPROVER, UserRole.ENGINEER)
        assert result.passed is True

    def test_engineer_cannot_approve(self, fabric):
        result = fabric.check_permission(UserRole.ENGINEER, UserRole.APPROVER, "approve")
        assert result.passed is False


class TestCheckHuman:
    """Check 8 — Human: AMBER/RED risk requires APPROVER sign-off."""

    def test_green_no_approval_needed(self, fabric):
        result = fabric.check_human(RiskLevel.GREEN)
        assert result.check_type == VerificationType.HUMAN
        assert result.passed is True

    def test_amber_without_approval_fails(self, fabric):
        result = fabric.check_human(RiskLevel.AMBER, None)
        assert result.passed is False

    def test_amber_with_approver_passes(self, fabric):
        approval = ApprovalDecision(
            task_id="t-1",
            status=ApprovalStatus.APPROVED,
            decided_by="user-1",
            decided_by_role=UserRole.APPROVER,
            risk_level=RiskLevel.AMBER,
        )
        result = fabric.check_human(RiskLevel.AMBER, approval)
        assert result.passed is True

    def test_amber_with_engineer_approval_fails(self, fabric):
        approval = ApprovalDecision(
            task_id="t-1",
            status=ApprovalStatus.APPROVED,
            decided_by="user-2",
            decided_by_role=UserRole.ENGINEER,
            risk_level=RiskLevel.AMBER,
        )
        result = fabric.check_human(RiskLevel.AMBER, approval)
        assert result.passed is False

    def test_red_requires_approval(self, fabric):
        result = fabric.check_human(RiskLevel.RED, None)
        assert result.passed is False


class TestFullVerification:
    """Test aggregate verification report."""

    def test_full_green_run_passes(self, fabric, sample_evidence, passing_calculations):
        report = fabric.run_full_verification(
            task_id="t-1",
            evidence_objects=sample_evidence,
            claimed_evidence_ids=[ev.evidence_id for ev in sample_evidence],
            source_hash="hash123",
            retrieval_query="pressure inspection",
            retrieved_evidence=sample_evidence,
            calculation_results=passing_calculations,
            schema_data={
                "task_id": "t-1",
                "document_id": "d-1",
                "calculations": [],
                "verification_report": {},
                "risk_level": "GREEN",
            },
            artifacts=[
                ArtifactRecord(
                    task_id="t-1", filename="test.docx", artifact_type="DOCX",
                    structural_valid=True, semantic_valid=True,
                ),
            ],
            user_role=UserRole.ENGINEER,
            risk_level=RiskLevel.GREEN,
        )
        assert report.overall_outcome == VerificationOutcome.PASS
        assert len(report.checks) == 8
        assert report.all_passed is True
