from __future__ import annotations

"""Sprint 4 – Verification Fabric.

Implements all 8 verification checks per Master PRD and Sprint Plan §10:
  1. Evidence    – every claim references a valid EvidenceObject with matching source_hash
  2. Retrieval   – retrieved evidence is relevant (above similarity threshold)
  3. Calculation  – deterministic recomputation matches within tolerance
  4. Rule        – business rules / regulatory thresholds satisfied
  5. Schema      – output conforms to DecisionPackage JSON schema
  6. Artifact    – files pass structural + semantic validation
  7. Permission  – action performed by user with required role
  8. Human       – AMBER/RED risk decisions have explicit APPROVER sign-off
"""

import logging
from typing import Any, Dict, List, Optional, Set

from app.schemas.decision_package import (
    ApprovalDecision,
    ArtifactManifest,
    ArtifactRecord,
    CalculationResult,
    VerificationCheckResult,
    VerificationReport,
)
from app.schemas.evidence import EvidenceObject
from shared.enums import (
    ApprovalStatus,
    RiskLevel,
    UserRole,
    VerificationOutcome,
    VerificationType,
)

logger = logging.getLogger(__name__)


class VerificationFabric:
    """Eight-check verification fabric for SAFIRE.

    Each check produces a VerificationCheckResult.  The fabric aggregates
    them into a VerificationReport with an overall pass/fail outcome.
    """

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def check_evidence(
        claimed_evidence_ids: List[str],
        available_evidence: List[EvidenceObject],
        source_hash: Optional[str] = None,
    ) -> VerificationCheckResult:
        """Check 1 — Evidence: every claim references a valid EvidenceObject."""
        available_ids: Set[str] = {ev.evidence_id for ev in available_evidence}
        missing = [eid for eid in claimed_evidence_ids if eid not in available_ids]

        if source_hash:
            hash_mismatches = [
                ev.evidence_id
                for ev in available_evidence
                if ev.evidence_id in claimed_evidence_ids
                and ev.source_hash != source_hash
            ]
        else:
            hash_mismatches = []

        passed = len(missing) == 0 and len(hash_mismatches) == 0
        detail_parts = []
        if missing:
            detail_parts.append(f"Missing evidence IDs: {missing}")
        if hash_mismatches:
            detail_parts.append(f"Hash mismatches: {hash_mismatches}")
        if passed:
            detail_parts.append(
                f"All {len(claimed_evidence_ids)} evidence references validated"
            )

        return VerificationCheckResult(
            check_type=VerificationType.EVIDENCE,
            passed=passed,
            detail="; ".join(detail_parts),
            evidence_ids=claimed_evidence_ids,
        )

    @staticmethod
    def check_retrieval(
        query: str,
        retrieved_evidence: List[EvidenceObject],
        min_relevance_score: float = 0.3,
    ) -> VerificationCheckResult:
        """Check 2 — Retrieval: retrieved evidence is relevant."""
        if not retrieved_evidence:
            return VerificationCheckResult(
                check_type=VerificationType.RETRIEVAL,
                passed=False,
                detail="No evidence retrieved for query",
            )

        # Simple relevance: check query terms appear in evidence text
        query_terms = set(query.lower().split())
        relevant_count = 0
        for ev in retrieved_evidence:
            ev_terms = set(ev.extracted_text.lower().split())
            overlap = len(query_terms & ev_terms) / max(len(query_terms), 1)
            if overlap >= min_relevance_score:
                relevant_count += 1

        passed = relevant_count > 0
        return VerificationCheckResult(
            check_type=VerificationType.RETRIEVAL,
            passed=passed,
            detail=f"{relevant_count}/{len(retrieved_evidence)} results relevant (threshold={min_relevance_score})",
            evidence_ids=[ev.evidence_id for ev in retrieved_evidence],
        )

    @staticmethod
    def check_calculation(
        calculation_results: List[CalculationResult],
    ) -> VerificationCheckResult:
        """Check 3 — Calculation: deterministic recomputation matches."""
        if not calculation_results:
            return VerificationCheckResult(
                check_type=VerificationType.CALCULATION,
                passed=False,
                detail="No calculations to verify",
            )

        mismatches = [r for r in calculation_results if not r.results_match]
        failures = [r for r in calculation_results if r.status == "FAIL"]

        passed = len(mismatches) == 0 and len(failures) == 0
        detail = (
            f"{len(calculation_results)} calculations verified: "
            f"{len(mismatches)} recomputation mismatches, "
            f"{len(failures)} threshold failures"
        )
        return VerificationCheckResult(
            check_type=VerificationType.CALCULATION,
            passed=passed,
            detail=detail,
            evidence_ids=[r.evidence_reference for r in calculation_results],
        )

    @staticmethod
    def check_rule(
        calculation_results: List[CalculationResult],
        custom_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> VerificationCheckResult:
        """Check 4 — Rule: business rules / regulatory thresholds satisfied."""
        violations: List[str] = []

        for result in calculation_results:
            if result.threshold_met is False:
                violations.append(
                    f"{result.parameter_name}: {result.primary_result} "
                    f"exceeds threshold {result.threshold}"
                )

        passed = len(violations) == 0
        detail = (
            f"All {len(calculation_results)} rules satisfied"
            if passed
            else f"Rule violations: {'; '.join(violations)}"
        )
        return VerificationCheckResult(
            check_type=VerificationType.RULE,
            passed=passed,
            detail=detail,
        )

    @staticmethod
    def check_schema(
        data: Dict[str, Any],
        required_fields: Optional[List[str]] = None,
    ) -> VerificationCheckResult:
        """Check 5 — Schema: output conforms to expected structure."""
        if required_fields is None:
            required_fields = [
                "task_id", "document_id", "calculations",
                "verification_report", "risk_level",
            ]

        missing = [f for f in required_fields if f not in data or data[f] is None]
        passed = len(missing) == 0
        detail = (
            f"All {len(required_fields)} required schema fields present"
            if passed
            else f"Missing schema fields: {missing}"
        )
        return VerificationCheckResult(
            check_type=VerificationType.SCHEMA,
            passed=passed,
            detail=detail,
        )

    @staticmethod
    def check_artifact(
        artifacts: List[ArtifactRecord],
    ) -> VerificationCheckResult:
        """Check 6 — Artifact: files pass structural + semantic validation."""
        if not artifacts:
            return VerificationCheckResult(
                check_type=VerificationType.ARTIFACT,
                passed=False,
                detail="No artifacts to validate",
            )

        structural_failures = [a for a in artifacts if not a.structural_valid]
        semantic_failures = [a for a in artifacts if not a.semantic_valid]

        passed = len(structural_failures) == 0 and len(semantic_failures) == 0
        detail = (
            f"All {len(artifacts)} artifacts pass validation"
            if passed
            else (
                f"Structural failures: {[a.filename for a in structural_failures]}; "
                f"Semantic failures: {[a.filename for a in semantic_failures]}"
            )
        )
        return VerificationCheckResult(
            check_type=VerificationType.ARTIFACT,
            passed=passed,
            detail=detail,
        )

    @staticmethod
    def check_permission(
        user_role: UserRole,
        required_role: UserRole,
        action: str = "approve",
    ) -> VerificationCheckResult:
        """Check 7 — Permission: user has the required role."""
        role_hierarchy = {
            UserRole.ADMIN: 3,
            UserRole.APPROVER: 2,
            UserRole.ENGINEER: 1,
        }
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        passed = user_level >= required_level
        detail = (
            f"User role {user_role} meets requirement {required_role} for '{action}'"
            if passed
            else f"User role {user_role} insufficient for '{action}' (requires {required_role})"
        )
        return VerificationCheckResult(
            check_type=VerificationType.PERMISSION,
            passed=passed,
            detail=detail,
        )

    @staticmethod
    def check_human(
        risk_level: RiskLevel,
        approval: Optional[ApprovalDecision] = None,
    ) -> VerificationCheckResult:
        """Check 8 — Human: AMBER/RED risk decisions require APPROVER sign-off."""
        if risk_level == RiskLevel.GREEN:
            return VerificationCheckResult(
                check_type=VerificationType.HUMAN,
                passed=True,
                detail="GREEN risk — no human approval required",
            )

        if approval is None or approval.status != ApprovalStatus.APPROVED:
            return VerificationCheckResult(
                check_type=VerificationType.HUMAN,
                passed=False,
                detail=f"{risk_level} risk requires explicit APPROVER sign-off; no valid approval found",
            )

        if approval.decided_by_role not in (UserRole.APPROVER, UserRole.ADMIN):
            return VerificationCheckResult(
                check_type=VerificationType.HUMAN,
                passed=False,
                detail=f"Approval by {approval.decided_by_role} invalid — only APPROVER/ADMIN may approve {risk_level} risk",
            )

        return VerificationCheckResult(
            check_type=VerificationType.HUMAN,
            passed=True,
            detail=f"{risk_level} risk approved by {approval.decided_by_role} ({approval.decided_by})",
        )

    # ------------------------------------------------------------------
    # Aggregate verification
    # ------------------------------------------------------------------

    def run_full_verification(
        self,
        task_id: str,
        evidence_objects: List[EvidenceObject],
        claimed_evidence_ids: List[str],
        source_hash: str,
        retrieval_query: str,
        retrieved_evidence: List[EvidenceObject],
        calculation_results: List[CalculationResult],
        schema_data: Dict[str, Any],
        artifacts: List[ArtifactRecord],
        user_role: UserRole,
        risk_level: RiskLevel,
        approval: Optional[ApprovalDecision] = None,
    ) -> VerificationReport:
        """Run all 8 verification checks and produce an aggregate report."""

        checks = [
            self.check_evidence(claimed_evidence_ids, evidence_objects, source_hash),
            self.check_retrieval(retrieval_query, retrieved_evidence),
            self.check_calculation(calculation_results),
            self.check_rule(calculation_results),
            self.check_schema(schema_data),
            self.check_artifact(artifacts),
            self.check_permission(user_role, UserRole.ENGINEER, "execute"),
            self.check_human(risk_level, approval),
        ]

        all_passed = all(c.passed for c in checks)
        outcome = VerificationOutcome.PASS if all_passed else VerificationOutcome.FAIL

        report = VerificationReport(
            task_id=task_id,
            checks=checks,
            overall_outcome=outcome,
            risk_level=risk_level,
        )

        logger.info(
            "Verification report for task %s: %s (%d/%d checks passed)",
            task_id, outcome, sum(1 for c in checks if c.passed), len(checks),
        )
        return report
