const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  current_state: string;
  state_history: StateTransition[];
  task_profile: TaskProfile;
  route_decision?: RouteResponse;
  routing_rationale?: string;
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
