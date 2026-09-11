/**
 * Sprint 7 — Demo Sequence API Client
 *
 * Fetches 21-step demo sequence results from the SAFIRE backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DemoStepResult {
  step_number: number;
  step_name: string;
  status: 'PASS' | 'FAIL' | 'SKIP' | 'PENDING';
  duration_ms: number;
  detail: string;
  data: Record<string, any>;
}

export interface DemoSequenceResult {
  run_id: string;
  started_at: string;
  completed_at: string;
  total_duration_ms: number;
  total_steps: number;
  passed_steps: number;
  failed_steps: number;
  skipped_steps: number;
  steps: DemoStepResult[];
  overall_status: 'PASS' | 'FAIL';
}

export interface TraceabilityRequirement {
  requirement_id: string;
  description: string;
  status: string;
  implementation_files: string[];
  test_files: string[];
  demo_step_numbers: number[];
  evidence_detail: string;
}

export interface TraceabilityReport {
  report_id: string;
  generated_at: string;
  total_requirements: number;
  implemented_count: number;
  partial_count: number;
  pending_count: number;
  requirements: TraceabilityRequirement[];
  overall_status: string;
}

export async function runDemoSequence(): Promise<DemoSequenceResult> {
  const res = await fetch(`${API_BASE}/v1/demo/sequence/run`, { method: 'POST' });
  if (!res.ok) throw new Error(`Demo sequence run failed: ${res.status}`);
  return res.json();
}

export async function getLatestDemoResult(): Promise<DemoSequenceResult> {
  const res = await fetch(`${API_BASE}/v1/demo/sequence/latest`);
  if (!res.ok) throw new Error(`Latest demo result failed: ${res.status}`);
  return res.json();
}

export async function getAllDemoResults(): Promise<DemoSequenceResult[]> {
  const res = await fetch(`${API_BASE}/v1/demo/sequence/results`);
  if (!res.ok) throw new Error(`Demo results failed: ${res.status}`);
  return res.json();
}

export async function getTraceabilityReport(): Promise<TraceabilityReport> {
  const res = await fetch(`${API_BASE}/v1/traceability/signoff`);
  if (!res.ok) throw new Error(`Traceability report failed: ${res.status}`);
  return res.json();
}
