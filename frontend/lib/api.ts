const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// --- Sprint 0–4 Types ---

export interface TaskProfile {
  task_id?: string;
  task_type: string;
  description: string;
  required_capabilities?: string[];
  input_data?: Record<string, any>;
  priority?: 'LOW' | 'MEDIUM' | 'HIGH';
  created_at?: string;
}

export interface StateTransition {
  from_state: string;
  to_state: string;
  timestamp: string;
  details?: string;
}

export interface RouteCandidate {
  model_id: string;
  model_name: string;
  composite_score: number;
  latency_score: number;
  vram_score: number;
  capability_bonus: number;
  feasible: boolean;
  reason: string;
}

export interface RouteResponse {
  selected_model: string;
  selected_model_name: string;
  matched_capabilities: string[];
  reasoning: string;
  context_window_size: number;
  estimated_latency_ms?: number;
  candidates?: RouteCandidate[];
  fallback_used?: boolean;
}

export interface TaskExecution {
  task_id: string;
  task_type: string;
  description: string;
  current_state: string;
  state_history: StateTransition[];
  // Routing — flat fields from backend
  selected_model_id?: string;
  selected_model_name?: string;
  routing_rationale?: string;
  required_capabilities?: string[];
  // Execution
  model_response?: string;
  started_at: string;
  completed_at?: string;
  error?: string;
}

export interface BenchmarkProfile {
  cold_start_latency_ms?: number;
  warm_inference_latency_ms?: number;
  model_load_time_ms?: number;
  model_switch_latency_ms?: number;
  vram_usage_mb?: number;
  throughput_tok_per_sec?: number;
  measured_at?: string;
}

export interface ModelRegistryEntry {
  model_id: string;
  name: string;
  capabilities: string[];
  context_length: number;
  latency_ms: number;
  runtime?: string;
  ollama_model?: string;
  model_family?: string;
  quantization?: string;
  vram_footprint_mb?: number;
  benchmark_profile?: BenchmarkProfile;
}

export interface NormalizedRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface EvidenceObject {
  evidence_id: string;
  document_id: string;
  source_hash: string;
  page_number: number;
  region: NormalizedRegion;
  extracted_text: string;
  confidence: number;
  evidence_type: 'TEXT_BLOCK' | 'TABLE' | 'STAMP' | 'SIGNATURE' | 'IMAGE' | 'KEY_VALUE';
  metadata?: Record<string, any>;
  created_at: string;
}

export interface DocumentMetadata {
  document_id: string;
  filename: string;
  file_size_bytes: number;
  sha256_hash: string;
  page_count: number;
  content_type: string;
  uploaded_at: string;
}

export interface VerticalSliceV0Response {
  execution_id: string;
  document_metadata: DocumentMetadata;
  evidence_count: number;
  evidence_objects: EvidenceObject[];
  retrieval_indexed_count: number;
  reasoning_summary: string;
  generated_artifact: Record<string, any>;
  pipeline_duration_ms: number;
  completed_at: string;
}

// --- Sprint 6 Types ---

export interface RoutingDecision {
  selected_model_id: string;
  selected_model_name: string;
  required_capabilities: string[];
  matched_capabilities: string[];
  routing_rationale: string;
  fallback_used: boolean;
  candidates_evaluated: number;
}

export interface EvidenceConflictRecord {
  parameter: string;
  evidence_a_id: string;
  evidence_a_value: string;
  evidence_b_id: string;
  evidence_b_value: string;
  severity: string;
  detail: string;
}

export interface SovereigntySnapshot {
  state: string;
  detail: string;
  checks_performed: number;
  is_sovereign: boolean;
}

export interface VerificationCheckResult {
  check_type: string;
  passed: boolean;
  detail: string;
  evidence_ids: string[];
  timestamp: string;
}

export interface VerificationReport {
  report_id: string;
  task_id: string;
  checks: VerificationCheckResult[];
  overall_outcome: string;
  risk_level: string;
}

export interface ApprovalDecision {
  approval_id: string;
  task_id: string;
  status: string;
  decided_by?: string;
  decided_by_role?: string;
  risk_level: string;
  reason: string;
}

export interface ArtifactRecord {
  artifact_id: string;
  task_id: string;
  filename: string;
  artifact_type: string;
  file_size_bytes: number;
  structural_valid: boolean;
  semantic_valid: boolean;
  evidence_references: string[];
}

export interface ArtifactManifest {
  manifest_id: string;
  task_id: string;
  artifacts: ArtifactRecord[];
  all_valid: boolean;
}

export interface FlagshipExecutionResult {
  execution_id: string;
  task_id: string;
  document_id: string;
  evidence_count: number;
  retrieval_results_count: number;
  calculations: any[];
  verification_report?: VerificationReport;
  approval?: ApprovalDecision;
  artifact_manifest?: ArtifactManifest;
  routing_decision?: RoutingDecision;
  sovereignty_snapshot?: SovereigntySnapshot;
  evidence_conflicts: EvidenceConflictRecord[];
  has_conflicts: boolean;
  audit_event_ids: string[];
  delivery_blocked: boolean;
  delivery_blocked_reason: string;
  risk_level: string;
  pipeline_states: string[];
  pipeline_duration_ms: number;
  completed_at: string;
}

export interface AuditEvent {
  event_id: string;
  event_type: string;
  detail: string;
  task_id?: string;
  timestamp: string;
}

export interface SovereigntyStatus {
  state: string;
  detail: string;
  is_sovereign: boolean;
  checks: any[];
  blocked_attempts: any[];
}

export interface DemoStatus {
  backend: { status: string };
  ollama: { status: string };
  docker: { status: string };
  sovereignty: { state: string };
  demo_readiness: string;
  limitations: string[];
}

// --- API Functions ---

export async function submitTask(taskType: string, description: string, inputData: Record<string, any> = {}, priority: string = 'MEDIUM'): Promise<TaskExecution> {
  const res = await fetch(`${API_BASE}/v1/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task_type: taskType,
      description,
      input_data: inputData,
      priority,
    }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Task submission failed: ${errorText}`);
  }
  return res.json();
}

export async function getTask(taskId: string): Promise<TaskExecution> {
  const res = await fetch(`${API_BASE}/v1/tasks/${taskId}`);
  if (!res.ok) throw new Error(`Failed to fetch task ${taskId}`);
  return res.json();
}

export async function listTasks(): Promise<TaskExecution[]> {
  const res = await fetch(`${API_BASE}/v1/tasks`);
  if (!res.ok) throw new Error('Failed to fetch tasks');
  return res.json();
}

export async function listModels(): Promise<ModelRegistryEntry[]> {
  const res = await fetch(`${API_BASE}/v1/models`);
  if (!res.ok) throw new Error('Failed to fetch models');
  return res.json();
}

export async function runBenchmark(modelId: string): Promise<BenchmarkProfile> {
  const res = await fetch(`${API_BASE}/v1/benchmark/${modelId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Benchmark failed for model ${modelId}`);
  return res.json();
}

export async function uploadDocument(): Promise<DocumentMetadata> {
  const res = await fetch(`${API_BASE}/v1/documents/upload`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Document upload failed');
  return res.json();
}

export async function getDocumentEvidence(documentId: string): Promise<EvidenceObject[]> {
  const res = await fetch(`${API_BASE}/v1/documents/${documentId}/evidence`);
  if (!res.ok) throw new Error(`Failed to fetch evidence for document ${documentId}`);
  return res.json();
}

export async function executeVerticalSliceV0(documentId: string): Promise<VerticalSliceV0Response> {
  const res = await fetch(`${API_BASE}/v1/documents/${documentId}/vertical-slice`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Vertical slice execution failed for ${documentId}`);
  return res.json();
}

// --- Sprint 5–6 API Functions ---

export async function executeFlagship(userRole: string = 'ENGINEER'): Promise<FlagshipExecutionResult> {
  const res = await fetch(`${API_BASE}/v1/flagship/execute?user_role=${userRole}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Flagship execution failed');
  return res.json();
}

export async function listFlagshipExecutions(): Promise<FlagshipExecutionResult[]> {
  const res = await fetch(`${API_BASE}/v1/flagship/`);
  if (!res.ok) throw new Error('Failed to list flagship executions');
  return res.json();
}

export async function listAuditEvents(): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/v1/audit/`);
  if (!res.ok) throw new Error('Failed to fetch audit events');
  return res.json();
}

export async function getSovereigntyStatus(): Promise<SovereigntyStatus> {
  const res = await fetch(`${API_BASE}/v1/sovereignty/status`);
  if (!res.ok) throw new Error('Failed to fetch sovereignty status');
  return res.json();
}

export async function runSovereigntySelfTest(): Promise<SovereigntyStatus> {
  const res = await fetch(`${API_BASE}/v1/sovereignty/self-test`, { method: 'POST' });
  if (!res.ok) throw new Error('Sovereignty self-test failed');
  return res.json();
}

export async function runSIABBenchmark(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/siab/run`, { method: 'POST' });
  if (!res.ok) throw new Error('SIAB benchmark failed');
  return res.json();
}

export async function getDemoStatus(): Promise<DemoStatus> {
  const res = await fetch(`${API_BASE}/v1/demo/status`);
  if (!res.ok) throw new Error('Failed to fetch demo status');
  return res.json();
}

export async function runSecurityDemo(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/demo/security`, { method: 'POST' });
  if (!res.ok) throw new Error('Security demo failed');
  return res.json();
}

export async function runConflictDemo(): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/demo/conflicts`, { method: 'POST' });
  if (!res.ok) throw new Error('Conflict demo failed');
  return res.json();
}

export async function runFlagshipDemo(userRole: string = 'ENGINEER'): Promise<FlagshipExecutionResult> {
  const res = await fetch(`${API_BASE}/v1/demo/flagship?user_role=${userRole}`, { method: 'POST' });
  if (!res.ok) throw new Error('Flagship demo failed');
  return res.json();
}

export async function approveTask(taskId: string, userId: string, userRole: string, reason: string = ''): Promise<ApprovalDecision> {
  const res = await fetch(`${API_BASE}/v1/tasks/${taskId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      user_role: userRole,
      action: 'APPROVED',
      reason,
    }),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Approval failed: ${errorText}`);
  }
  return res.json();
}
