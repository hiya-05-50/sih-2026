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

export const ModelCapability = {
  TEXT: "TEXT",
  VISION: "VISION",
  OCR: "OCR",
  DOCUMENT_UNDERSTANDING: "DOCUMENT_UNDERSTANDING",
  REASONING: "REASONING",
  CODING: "CODING",
  TOOL_CALLING: "TOOL_CALLING",
  STRUCTURED_OUTPUT: "STRUCTURED_OUTPUT",
  LONG_CONTEXT: "LONG_CONTEXT",
  EMBEDDING: "EMBEDDING",
  RERANKING: "RERANKING",
} as const;
export type ModelCapability =
  (typeof ModelCapability)[keyof typeof ModelCapability];

export const PipelineCapability = {
  RETRIEVAL: "RETRIEVAL",
  EVIDENCE_EXTRACTION: "EVIDENCE_EXTRACTION",
  CALCULATION: "CALCULATION",
  VALIDATION: "VALIDATION",
  DOCUMENT_GENERATION: "DOCUMENT_GENERATION",
  SPREADSHEET_GENERATION: "SPREADSHEET_GENERATION",
  ARTIFACT_GENERATION: "ARTIFACT_GENERATION",
} as const;
export type PipelineCapability =
  (typeof PipelineCapability)[keyof typeof PipelineCapability];
