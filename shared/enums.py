"""SAFIRE canonical enums.

These enums define the shared vocabulary used across backend and frontend.
They are the contract-freeze artifacts for Sprint 0.
"""

from enum import StrEnum


class TaskState(StrEnum):
    INTAKE = "INTAKE"
    CLASSIFY = "CLASSIFY"
    PLAN = "PLAN"
    RETRIEVE = "RETRIEVE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    APPROVE = "APPROVE"
    DELIVER = "DELIVER"
    AUDIT = "AUDIT"
    FAILED = "FAILED"


class RiskLevel(StrEnum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


class VerificationOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ESCALATE = "ESCALATE"
    APPROVE = "APPROVE"


class SovereigntyState(StrEnum):
    NOT_READY = "NOT_READY"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class UserRole(StrEnum):
    ENGINEER = "ENGINEER"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"


class ArtifactStatus(StrEnum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    VALID = "VALID"
    INVALID = "INVALID"
    DELIVERED = "DELIVERED"


class ModelCapability(StrEnum):
    TEXT = "TEXT"
    VISION = "VISION"
    OCR = "OCR"
    DOCUMENT_UNDERSTANDING = "DOCUMENT_UNDERSTANDING"
    REASONING = "REASONING"
    CODING = "CODING"
    TOOL_CALLING = "TOOL_CALLING"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    LONG_CONTEXT = "LONG_CONTEXT"
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"


class PipelineCapability(StrEnum):
    RETRIEVAL = "RETRIEVAL"
    EVIDENCE_EXTRACTION = "EVIDENCE_EXTRACTION"
    CALCULATION = "CALCULATION"
    VALIDATION = "VALIDATION"
    DOCUMENT_GENERATION = "DOCUMENT_GENERATION"
    SPREADSHEET_GENERATION = "SPREADSHEET_GENERATION"
    ARTIFACT_GENERATION = "ARTIFACT_GENERATION"


class EvidenceType(StrEnum):
    TEXT_BLOCK = "TEXT_BLOCK"
    TABLE = "TABLE"
    STAMP = "STAMP"
    SIGNATURE = "SIGNATURE"
    IMAGE = "IMAGE"
    KEY_VALUE = "KEY_VALUE"

