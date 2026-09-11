/**
 * Sprint 7 — Sovereignty Dashboard API Client
 *
 * Fetches sovereignty status, blocked attempts, and self-test results
 * from the SAFIRE backend sovereignty endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SovereigntyCheckResult {
  check_name: string;
  passed: boolean;
  detail: string;
}

export interface BlockedAttempt {
  source: string;
  destination: string;
  reason: string;
  timestamp?: string;
}

export interface SovereigntyStatus {
  state: 'READY' | 'NOT_READY' | 'DEGRADED' | 'FAILED';
  checks: SovereigntyCheckResult[];
  blocked_attempts: BlockedAttempt[];
  external_connections: number;
  external_dns_queries: number;
  cloud_api_calls: number;
  last_check_at: string;
  detail: string;
}

export async function getSovereigntyStatus(): Promise<SovereigntyStatus> {
  const res = await fetch(`${API_BASE}/v1/sovereignty/status`);
  if (!res.ok) throw new Error(`Sovereignty status failed: ${res.status}`);
  return res.json();
}

export async function runSovereigntySelfTest(): Promise<SovereigntyStatus> {
  const res = await fetch(`${API_BASE}/v1/sovereignty/self-test`, { method: 'POST' });
  if (!res.ok) throw new Error(`Self-test failed: ${res.status}`);
  return res.json();
}

export async function getBlockedAttempts(): Promise<BlockedAttempt[]> {
  const res = await fetch(`${API_BASE}/v1/sovereignty/blocked`);
  if (!res.ok) throw new Error(`Blocked attempts failed: ${res.status}`);
  return res.json();
}
