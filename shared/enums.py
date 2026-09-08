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
