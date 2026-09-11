from __future__ import annotations

"""Sprint 7 – Traceability Sign-Off Service.

Generates the formal PRD §41 traceability matrix mapping all 13 PS
requirements (R1–R13) to concrete implementation evidence, test evidence,
and demo step numbers.

Every cell is either real evidence or 'TO BE VALIDATED' — never fabricated.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class RequirementEvidence(BaseModel):
    """Evidence for a single PS requirement."""

    requirement_id: str = Field(..., description="e.g. R1, R2, ...")
    description: str = Field(..., description="Requirement description")
    status: str = Field("IMPLEMENTED", description="IMPLEMENTED | PARTIAL | TO BE VALIDATED")
    implementation_files: List[str] = Field(default_factory=list, description="Backend files implementing this")
    test_files: List[str] = Field(default_factory=list, description="Test files verifying this")
    demo_step_numbers: List[int] = Field(default_factory=list, description="Judge demo steps that demonstrate this")
    evidence_detail: str = Field("", description="Human-readable explanation of evidence")


class TraceabilityReport(BaseModel):
    """Full traceability sign-off report."""

    report_id: str = Field(default="")
    generated_at: str = Field(default="")
    total_requirements: int = 0
    implemented_count: int = 0
    partial_count: int = 0
    pending_count: int = 0
    requirements: List[RequirementEvidence] = Field(default_factory=list)
    overall_status: str = Field("", description="COMPLETE | PARTIAL | INCOMPLETE")


# ---------------------------------------------------------------------------
# Traceability Matrix
# ---------------------------------------------------------------------------

# The canonical 13 PS requirements from Master PRD §41
_REQUIREMENTS: List[RequirementEvidence] = [
    RequirementEvidence(
        requirement_id="R1",
        description="Air-gapped, on-prem (Sovereignty)",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/sovereignty.py",
            "app/api/sovereignty.py",
        ],
        test_files=[
            "tests/test_sovereignty.py",
            "tests/test_sprint5_acceptance.py::TestSovereigntyAPI",
        ],
        demo_step_numbers=[15, 16],
        evidence_detail=(
            "SovereigntyMonitor performs real TCP/DNS/API-binding self-tests. "
            "Reports NOT_READY honestly when external connectivity is detected. "
            "Live dashboard shows zero-egress during flagship run."
        ),
    ),
    RequirementEvidence(
        requirement_id="R2",
        description="Multiple open-weight models",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/registry.py",
            "app/adapters/manager.py",
            "app/adapters/ollama.py",
        ],
        test_files=[
            "tests/test_model_registry.py",
            "tests/test_model_adapter.py",
            "tests/test_adapter_manager.py",
        ],
        demo_step_numbers=[6],
        evidence_detail=(
            "ModelRegistry supports dynamic registration of multiple models. "
            "Ollama adapter provides real inference. Fixture adapter for testing."
        ),
    ),
    RequirementEvidence(
        requirement_id="R3",
        description="Automatic model selection",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/router.py",
        ],
        test_files=[
            "tests/test_router.py",
        ],
        demo_step_numbers=[6],
        evidence_detail=(
            "Deterministic capability-filter → feasibility-filter → scoring → "
            "selection → fallback pipeline. Routing rationale visible in UI."
        ),
    ),
    RequirementEvidence(
        requirement_id="R4",
        description="Extensible without redesign",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/registry.py",
            "app/adapters/base.py",
            "app/services/tools/registry.py",
        ],
        test_files=[
            "tests/test_registry_service.py",
            "tests/test_tool_registry.py",
        ],
        demo_step_numbers=[],
        evidence_detail=(
            "Registry and adapter interfaces support plug-in extension. "
            "Tool registry with schema-based registration."
        ),
    ),
    RequirementEvidence(
        requirement_id="R5",
        description="Genuine agentic behavior",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/agent/loop.py",
            "app/services/agent/state.py",
            "app/services/flagship_pipeline.py",
        ],
        test_files=[
            "tests/test_agent_loop.py",
            "tests/test_flagship_pipeline.py",
        ],
        demo_step_numbers=[17],
        evidence_detail=(
            "Plan-act-observe-verify loop with bounded execution. "
            "Agent state machine with MAX_AGENT_STEPS, MAX_TOOL_CALLS enforcement."
        ),
    ),
    RequirementEvidence(
        requirement_id="R6",
        description="Local file read/write",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/tools/implementations.py",
        ],
        test_files=[
            "tests/test_tool_registry.py",
        ],
        demo_step_numbers=[17],
        evidence_detail="Tool registry includes structured_file_read and structured_file_write tools.",
    ),
    RequirementEvidence(
        requirement_id="R7",
        description="Sandboxed code execution",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/tools/sandbox.py",
        ],
        test_files=[
            "tests/test_sandbox.py",
        ],
        demo_step_numbers=[17],
        evidence_detail=(
            "Rootless Docker with --network none, resource limits, "
            "captured stdout/stderr. Assumes Docker on target OS."
        ),
    ),
    RequirementEvidence(
        requirement_id="R8",
        description="Spreadsheet work",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/artifact_engine.py",
        ],
        test_files=[
            "tests/test_artifact_engine.py",
        ],
        demo_step_numbers=[11],
        evidence_detail=(
            "Inspection_Data.xlsx with required columns: "
            "measurement, current_value, threshold, status, evidence_reference."
        ),
    ),
    RequirementEvidence(
        requirement_id="R9",
        description="Internal knowledge search",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/retrieval_index.py",
        ],
        test_files=[
            "tests/test_retrieval_index.py",
        ],
        demo_step_numbers=[5],
        evidence_detail="EvidenceRetrievalIndex provides hybrid search over ingested evidence.",
    ),
    RequirementEvidence(
        requirement_id="R10",
        description="Multimodal understanding",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/vision_gateway.py",
            "app/services/document_parser.py",
        ],
        test_files=[
            "tests/test_document_parser.py",
        ],
        demo_step_numbers=[3, 18],
        evidence_detail="Targeted vision calls through model gateway for document pages.",
    ),
    RequirementEvidence(
        requirement_id="R11",
        description="OCR capability",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/document_parser.py",
        ],
        test_files=[
            "tests/test_document_parser.py",
        ],
        demo_step_numbers=[3],
        evidence_detail="Document parser with OCR extraction, layout analysis, and evidence object creation.",
    ),
    RequirementEvidence(
        requirement_id="R12",
        description="Real deliverables",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/artifact_engine.py",
        ],
        test_files=[
            "tests/test_artifact_engine.py",
        ],
        demo_step_numbers=[10, 11, 12],
        evidence_detail=(
            "Decision_Note.docx, Inspection_Data.xlsx, Evidence_Report.pdf — "
            "all with structural + semantic validation."
        ),
    ),
    RequirementEvidence(
        requirement_id="R13",
        description="Visible zero-egress proof",
        status="IMPLEMENTED",
        implementation_files=[
            "app/services/sovereignty.py",
            "app/services/audit.py",
        ],
        test_files=[
            "tests/test_sovereignty.py",
            "tests/test_audit.py",
        ],
        demo_step_numbers=[14, 15, 16],
        evidence_detail=(
            "Live sovereignty monitor + blocked-attempt log + audit trail. "
            "Controlled blocked network attempt in demo step 16."
        ),
    ),
]


class TraceabilityService:
    """Generates and serves the formal traceability sign-off report."""

    def generate_report(self) -> TraceabilityReport:
        """Generate the full traceability matrix report."""
        requirements = [r.model_copy() for r in _REQUIREMENTS]

        implemented = sum(1 for r in requirements if r.status == "IMPLEMENTED")
        partial = sum(1 for r in requirements if r.status == "PARTIAL")
        pending = sum(1 for r in requirements if r.status == "TO BE VALIDATED")

        if implemented == len(requirements):
            overall = "COMPLETE"
        elif pending == len(requirements):
            overall = "INCOMPLETE"
        else:
            overall = "PARTIAL"

        report = TraceabilityReport(
            report_id=f"trace-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_requirements=len(requirements),
            implemented_count=implemented,
            partial_count=partial,
            pending_count=pending,
            requirements=requirements,
            overall_status=overall,
        )

        logger.info(
            "Traceability report %s: %d/%d implemented, status=%s",
            report.report_id, implemented, len(requirements), overall,
        )
        return report
