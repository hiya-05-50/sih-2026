from __future__ import annotations

"""Sprint 4 – Flagship Pipeline Orchestrator.

Wires the full end-to-end flagship path for the first time:
  UPLOAD → OCR/VISION → EVIDENCE → RETRIEVAL → REASONING →
  DETERMINISTIC COMPUTE → VERIFICATION → RISK → APPROVAL → ARTIFACT

Produces Vertical Slice V3 — the complete decision package pipeline.
"""

import logging
import time
import uuid
from typing import List, Optional

from app.adapters.manager import AdapterManager
from app.schemas.decision_package import (
    ApprovalDecision,
    CalculationResult,
    FlagshipExecutionResult,
    VerificationReport,
)
from app.schemas.evidence import EvidenceObject
from app.services.approval import ApprovalService
from app.services.artifact_engine import ArtifactEngine
from app.services.deterministic_compute import DeterministicComputeEngine
from app.services.document_parser import DocumentParser
from app.services.retrieval_index import EvidenceRetrievalIndex
from app.services.verification import VerificationFabric
from shared.enums import RiskLevel, UserRole, VerificationOutcome

logger = logging.getLogger(__name__)


class FlagshipPipeline:
    """Orchestrates the complete flagship workflow end-to-end.

    Each stage is explicitly traced with pipeline_states for full auditability.
    """

    def __init__(
        self,
        adapter_manager: AdapterManager,
        approval_service: ApprovalService,
    ) -> None:
        self._adapter_manager = adapter_manager
        self._parser = DocumentParser()
        self._retrieval = EvidenceRetrievalIndex()
        self._compute = DeterministicComputeEngine()
        self._verification = VerificationFabric()
        self._artifact_engine = ArtifactEngine()
        self._approval = approval_service

        # In-memory execution store
        self._executions: dict[str, FlagshipExecutionResult] = {}

    async def execute(
        self,
        document_id: Optional[str] = None,
        document_content: Optional[bytes] = None,
        user_role: UserRole = UserRole.ENGINEER,
    ) -> FlagshipExecutionResult:
        """Execute the full flagship pipeline.

        Args:
            document_id: ID of the document to process.
            document_content: Raw document bytes (or sample will be generated).
            user_role: Role of the user initiating the pipeline.

        Returns:
            FlagshipExecutionResult with full traceability.
        """
        start_time = time.time()
        task_id = f"flagship-{uuid.uuid4().hex[:8]}"

        result = FlagshipExecutionResult(
            task_id=task_id,
        )

        try:
            # --- STAGE 1: UPLOAD ---
            result.pipeline_states.append("UPLOAD")
            if document_content is None:
                meta, document_content = self._parser.generate_sample_inspection_report(document_id)
                document_id = meta.document_id
            else:
                from app.schemas.evidence import DocumentMetadata
                document_id = document_id or f"doc-{uuid.uuid4().hex[:8]}"
                sha256 = self._parser.compute_sha256(document_content)
                meta = DocumentMetadata(
                    document_id=document_id,
                    filename="uploaded_document.pdf",
                    file_size_bytes=len(document_content),
                    sha256_hash=sha256,
                )

            result.document_id = document_id
            logger.info("Flagship [%s] UPLOAD: doc=%s", task_id, document_id)

            # --- STAGE 2: OCR/VISION ---
            pipeline_states.append("OCR_VISION")
            parse_response = await self._parser.parse_document(
                document_id=document_id,
                content=document_content,
                filename=meta.filename,
                enable_targeted_vision=True,
            )
            evidence_objects = parse_response.evidence_objects
            result.evidence_count = len(evidence_objects)
            logger.info(
                "Flagship [%s] OCR/VISION: %d evidence objects",
                task_id, len(evidence_objects),
            )

            # --- STAGE 3: EVIDENCE ---
            pipeline_states.append("EVIDENCE")
            # Evidence objects are already created by parser

            # --- STAGE 4: RETRIEVAL ---
            pipeline_states.append("RETRIEVAL")
            self._retrieval.clear()
            self._retrieval.ingest_batch(evidence_objects)
            retrieved = self._retrieval.search_evidence("inspection compliance", top_k=5)
            result.retrieval_results_count = len(retrieved)
            logger.info(
                "Flagship [%s] RETRIEVAL: %d results", task_id, len(retrieved),
            )

            # --- STAGE 5: REASONING ---
            pipeline_states.append("REASONING")
            # In Sprint 4, reasoning produces structured extraction
            # that feeds deterministic compute. The fixture/real model
            # was already used in S3 for the agent loop.

            # --- STAGE 6: DETERMINISTIC COMPUTE ---
            pipeline_states.append("DETERMINISTIC_COMPUTE")
            calc_requests = self._compute.build_inspection_calculations(evidence_objects)
            calculation_results = self._compute.execute_batch(calc_requests)
            result.calculations = calculation_results
            logger.info(
                "Flagship [%s] COMPUTE: %d calculations (%d passed)",
                task_id,
                len(calculation_results),
                sum(1 for c in calculation_results if c.status == "PASS"),
            )

            # --- STAGE 7: VERIFICATION ---
            pipeline_states.append("VERIFICATION")
            claimed_ids = [ev.evidence_id for ev in evidence_objects]
            schema_data = {
                "task_id": task_id,
                "document_id": document_id,
                "calculations": [c.model_dump() for c in calculation_results],
                "verification_report": None,  # Will be filled
                "risk_level": None,  # Will be filled
            }

            # Run verification without artifacts first (they don't exist yet)
            # Artifact check will be re-run after generation
            verification_report = self._verification.run_full_verification(
                task_id=task_id,
                evidence_objects=evidence_objects,
                claimed_evidence_ids=claimed_ids,
                source_hash=parse_response.source_hash,
                retrieval_query="inspection compliance",
                retrieved_evidence=retrieved,
                calculation_results=calculation_results,
                schema_data=schema_data,
                artifacts=[],  # Will validate post-generation
                user_role=user_role,
                risk_level=RiskLevel.GREEN,  # Will be updated
                approval=None,
            )
            result.verification_report = verification_report

            # --- STAGE 8: RISK CLASSIFICATION ---
            pipeline_states.append("RISK")
            # Determine risk based on calculation results
            any_failures = any(c.status == "FAIL" for c in calculation_results)
            if any_failures:
                risk_level = RiskLevel.RED
            elif any(c.threshold_met is False for c in calculation_results):
                risk_level = RiskLevel.AMBER
            else:
                risk_level = RiskLevel.GREEN

            result.risk_level = risk_level
            verification_report.risk_level = risk_level
            logger.info("Flagship [%s] RISK: %s", task_id, risk_level)

            # --- STAGE 9: APPROVAL ---
            pipeline_states.append("APPROVAL")
            approval: Optional[ApprovalDecision] = None
            if risk_level in (RiskLevel.AMBER, RiskLevel.RED):
                approval = self._approval.request_approval(task_id, risk_level)
                result.approval = approval
                logger.info(
                    "Flagship [%s] APPROVAL: %s risk — approval required (status=%s)",
                    task_id, risk_level, approval.status,
                )
            else:
                logger.info("Flagship [%s] APPROVAL: GREEN — no approval needed", task_id)

            # --- STAGE 10: ARTIFACT GENERATION ---
            pipeline_states.append("ARTIFACT")
            # Check delivery permission
            delivery_allowed, delivery_reason = self._approval.check_delivery_allowed(
                task_id, risk_level
            )

            if delivery_allowed:
                manifest = self._artifact_engine.generate_full_manifest(
                    task_id=task_id,
                    title="Substation Delta-4 Inspection Decision Note",
                    summary=(
                        f"Automated inspection analysis: {len(evidence_objects)} evidence objects, "
                        f"{len(calculation_results)} deterministic calculations, "
                        f"verification: {verification_report.overall_outcome}"
                    ),
                    evidence_objects=evidence_objects,
                    calculation_results=calculation_results,
                    verification_report=verification_report,
                )
                result.artifact_manifest = manifest
                logger.info(
                    "Flagship [%s] ARTIFACT: %d files generated (all_valid=%s)",
                    task_id, len(manifest.artifacts), manifest.all_valid,
                )
            else:
                logger.info(
                    "Flagship [%s] ARTIFACT: delivery blocked — %s",
                    task_id, delivery_reason,
                )

        except Exception as exc:
            pipeline_states.append("FAILED")
            logger.error("Flagship [%s] FAILED: %s", task_id, exc)
            raise

        # Finalize
        result.pipeline_duration_ms = (time.time() - start_time) * 1000.0
        self._executions[task_id] = result

        logger.info(
            "Flagship [%s] COMPLETE: %d stages in %.1fms",
            task_id, len(pipeline_states), result.pipeline_duration_ms,
        )
        return result

    def get_execution(self, task_id: str) -> Optional[FlagshipExecutionResult]:
        """Retrieve a flagship execution by task ID."""
        return self._executions.get(task_id)

    def list_executions(self) -> list[FlagshipExecutionResult]:
        """List all flagship executions."""
        return list(self._executions.values())
