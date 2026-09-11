from __future__ import annotations

"""Sprint 4 – Decision Package & Verification Schemas.

Defines the structured output contracts for the full flagship pipeline:
  DecisionPackage → CalculationResult → VerificationReport → ApprovalDecision → ArtifactManifest
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.enums import (
    ApprovalStatus,
    RiskLevel,
    UserRole,
    VerificationOutcome,
    VerificationType,
)


# ---------------------------------------------------------------------------
# Deterministic Compute
# ---------------------------------------------------------------------------


class CalculationRequest(BaseModel):
    """Structured computation input extracted from evidence by LLM/VLM."""

    calc_id: str = Field(
        default_factory=lambda: f"calc-{uuid.uuid4().hex[:8]}",
        description="Unique calculation identifier",
    )
    parameter_name: str = Field(..., description="Name of the parameter being calculated (e.g. 'vibration_level')")
    formula: str = Field(..., description="Mathematical formula or rule to apply")
    input_values: Dict[str, float] = Field(..., description="Named input values for the formula")
    threshold: Optional[float] = Field(None, description="Regulatory/compliance threshold")
    threshold_operator: str = Field(
        "<=", description="Comparison operator for threshold (<=, >=, <, >, ==)"
    )
    tolerance: float = Field(0.0, ge=0.0, description="Tolerance for comparison (0.0 = exact)")
    evidence_reference: str = Field(..., description="Evidence Object ID this calculation is derived from")
    unit: str = Field("", description="Unit of measurement (e.g. 'mm/s', '°C', 'Bar')")


class CalculationResult(BaseModel):
    """Result of a deterministic computation with independent recomputation."""

    calc_id: str = Field(..., description="Calculation ID")
    parameter_name: str = Field(..., description="Parameter being calculated")
    primary_result: float = Field(..., description="Result from primary computation")
    recomputed_result: float = Field(..., description="Result from independent recomputation")
    results_match: bool = Field(..., description="Whether primary and recomputed results match within tolerance")
    threshold: Optional[float] = Field(None, description="Applied threshold")
    threshold_met: Optional[bool] = Field(None, description="Whether result meets threshold requirement")
    status: str = Field(..., description="PASS or FAIL")
    evidence_reference: str = Field(..., description="Evidence Object ID")
    formula_used: str = Field(..., description="Formula that was applied")
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full provenance chain: evidence → extraction → compute → recompute → compare",
    )


# ---------------------------------------------------------------------------
# Verification Fabric
# ---------------------------------------------------------------------------


class VerificationCheckResult(BaseModel):
    """Result of a single verification check."""

    check_type: VerificationType = Field(..., description="Type of verification check")
    passed: bool = Field(..., description="Whether the check passed")
    detail: str = Field("", description="Human-readable explanation")
    evidence_ids: List[str] = Field(default_factory=list, description="Referenced evidence IDs")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class VerificationReport(BaseModel):
    """Aggregate verification report containing all 8 checks."""

    report_id: str = Field(
        default_factory=lambda: f"vr-{uuid.uuid4().hex[:8]}"
    )
    task_id: str = Field(..., description="Task being verified")
    checks: List[VerificationCheckResult] = Field(
        default_factory=list, description="Results of all verification checks"
    )
    overall_outcome: VerificationOutcome = Field(
        default=VerificationOutcome.FAIL, description="Aggregate outcome"
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.GREEN, description="Risk classification"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> List[VerificationCheckResult]:
        return [c for c in self.checks if not c.passed]


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------


class ApprovalDecision(BaseModel):
    """An approval decision on a task."""

    approval_id: str = Field(
        default_factory=lambda: f"apr-{uuid.uuid4().hex[:8]}"
    )
    task_id: str = Field(..., description="Task being approved")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Current approval status"
    )
    decided_by: Optional[str] = Field(None, description="User ID of the decision maker")
    decided_by_role: Optional[UserRole] = Field(None, description="Role of the decision maker")
    risk_level: RiskLevel = Field(default=RiskLevel.GREEN, description="Risk level at time of decision")
    reason: str = Field("", description="Reason for approval/rejection")
    decided_at: Optional[str] = Field(None, description="ISO-8601 timestamp of decision")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ApprovalRequest(BaseModel):
    """Request to approve or reject a task."""

    user_id: str = Field(..., description="User making the decision")
    user_role: UserRole = Field(..., description="Role of the user")
    action: ApprovalStatus = Field(..., description="APPROVED or REJECTED")
    reason: str = Field("", description="Reason for the decision")


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


class ArtifactRecord(BaseModel):
    """Record of a generated artifact file."""

    artifact_id: str = Field(
        default_factory=lambda: f"art-{uuid.uuid4().hex[:8]}"
    )
    task_id: str = Field(..., description="Task that produced this artifact")
    filename: str = Field(..., description="Output filename")
    artifact_type: str = Field(..., description="DOCX, XLSX, or PDF")
    file_size_bytes: int = Field(0, description="Size in bytes")
    structural_valid: bool = Field(False, description="Passes structural validation")
    semantic_valid: bool = Field(False, description="Passes semantic validation")
    content: Optional[bytes] = Field(None, exclude=True, description="Raw file content")
    evidence_references: List[str] = Field(
        default_factory=list, description="Evidence IDs referenced in this artifact"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ArtifactManifest(BaseModel):
    """The complete set of artifacts produced by a flagship run."""

    manifest_id: str = Field(
        default_factory=lambda: f"mfst-{uuid.uuid4().hex[:8]}"
    )
    task_id: str = Field(..., description="Task ID")
    artifacts: List[ArtifactRecord] = Field(default_factory=list)
    all_valid: bool = Field(False, description="All artifacts pass both validation dimensions")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Flagship Execution
# ---------------------------------------------------------------------------


class FlagshipExecutionResult(BaseModel):
    """Complete result of a flagship pipeline execution (Vertical Slice V3)."""

    execution_id: str = Field(
        default_factory=lambda: f"flg-{uuid.uuid4().hex[:8]}"
    )
    task_id: str = Field(..., description="Task ID")

    # Pipeline stages
    document_id: str = Field("", description="Source document ID")
    evidence_count: int = Field(0, description="Number of Evidence Objects extracted")
    retrieval_results_count: int = Field(0, description="Number of retrieval hits")
    calculations: List[CalculationResult] = Field(default_factory=list)
    verification_report: Optional[VerificationReport] = None
    approval: Optional[ApprovalDecision] = None
    artifact_manifest: Optional[ArtifactManifest] = None

    # Traceability
    risk_level: RiskLevel = Field(default=RiskLevel.GREEN)
    pipeline_states: List[str] = Field(
        default_factory=list, description="Ordered list of pipeline states traversed"
    )
    pipeline_duration_ms: float = Field(0.0)
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
