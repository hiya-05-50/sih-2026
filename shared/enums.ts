/**
 * SAFIRE canonical enums.
 *
 * These enums mirror the Python definitions in shared/enums.py.
 * They are the contract-freeze artifacts for Sprint 0.
 */

export const TaskState = {
  INTAKE: "INTAKE",
  CLASSIFY: "CLASSIFY",
  PLAN: "PLAN",
  RETRIEVE: "RETRIEVE",
  OBSERVE: "OBSERVE",
  VERIFY: "VERIFY",
  APPROVE: "APPROVE",
  DELIVER: "DELIVER",
  AUDIT: "AUDIT",
  FAILED: "FAILED",
} as const;
export type TaskState = (typeof TaskState)[keyof typeof TaskState];

export const RiskLevel = {
  GREEN: "GREEN",
  AMBER: "AMBER",
  RED: "RED",
} as const;
export type RiskLevel = (typeof RiskLevel)[keyof typeof RiskLevel];

export const VerificationOutcome = {
  PASS: "PASS",
  FAIL: "FAIL",
  ESCALATE: "ESCALATE",
  APPROVE: "APPROVE",
} as const;
export type VerificationOutcome =
  (typeof VerificationOutcome)[keyof typeof VerificationOutcome];

export const SovereigntyState = {
  NOT_READY: "NOT_READY",
  READY: "READY",
  DEGRADED: "DEGRADED",
  FAILED: "FAILED",
} as const;
export type SovereigntyState =
  (typeof SovereigntyState)[keyof typeof SovereigntyState];

export const UserRole = {
  ENGINEER: "ENGINEER",
  APPROVER: "APPROVER",
  ADMIN: "ADMIN",
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const ArtifactStatus = {
  PENDING: "PENDING",
  VALIDATING: "VALIDATING",
  VALID: "VALID",
  INVALID: "INVALID",
  DELIVERED: "DELIVERED",
} as const;
export type ArtifactStatus =
  (typeof ArtifactStatus)[keyof typeof ArtifactStatus];

export const EvidenceType = {
  TEXT_BLOCK: "TEXT_BLOCK",
  TABLE: "TABLE",
  STAMP: "STAMP",
  SIGNATURE: "SIGNATURE",
  IMAGE: "IMAGE",
  KEY_VALUE: "KEY_VALUE",
} as const;
export type EvidenceType =
  (typeof EvidenceType)[keyof typeof EvidenceType];

// ---------------------------------------------------------------------------
// Sprint 5 — Sovereignty + Security + SIAB
// ---------------------------------------------------------------------------

export const NetworkZone = {
  LOOPBACK: "LOOPBACK",
  TRUSTED_ONPREM: "TRUSTED_ONPREM",
  EXTERNAL: "EXTERNAL",
} as const;
export type NetworkZone = (typeof NetworkZone)[keyof typeof NetworkZone];

export const SovereigntyEventType = {
  NETWORK_BLOCKED: "NETWORK_BLOCKED",
  NETWORK_ALLOWED: "NETWORK_ALLOWED",
  DNS_QUERY: "DNS_QUERY",
  DNS_BLOCKED: "DNS_BLOCKED",
  ZONE_VIOLATION: "ZONE_VIOLATION",
  TOOL_BLOCKED: "TOOL_BLOCKED",
  TOOL_ALLOWED: "TOOL_ALLOWED",
  PROMPT_INJECTION_DETECTED: "PROMPT_INJECTION_DETECTED",
  SANDBOX_ESCAPE_ATTEMPT: "SANDBOX_ESCAPE_ATTEMPT",
  SELF_TEST_RESULT: "SELF_TEST_RESULT",
  READINESS_CHANGE: "READINESS_CHANGE",
  STARTUP: "STARTUP",
  SHUTDOWN: "SHUTDOWN",
} as const;
export type SovereigntyEventType =
  (typeof SovereigntyEventType)[keyof typeof SovereigntyEventType];

export const SovereigntyEventSeverity = {
  INFO: "INFO",
  WARNING: "WARNING",
  CRITICAL: "CRITICAL",
} as const;
export type SovereigntyEventSeverity =
  (typeof SovereigntyEventSeverity)[keyof typeof SovereigntyEventSeverity];

export const TrustBoundary = {
  SYSTEM: "SYSTEM",
  USER: "USER",
  TOOL_OUTPUT: "TOOL_OUTPUT",
  DOCUMENT_CONTENT: "DOCUMENT_CONTENT",
  MODEL_RESPONSE: "MODEL_RESPONSE",
} as const;
export type TrustBoundary =
  (typeof TrustBoundary)[keyof typeof TrustBoundary];

export const SIABConfig = {
  BARE_MODEL: "BARE_MODEL",
  AGENT_NO_FABRIC: "AGENT_NO_FABRIC",
  FULL_SAFIRE: "FULL_SAFIRE",
} as const;
export type SIABConfig = (typeof SIABConfig)[keyof typeof SIABConfig];
