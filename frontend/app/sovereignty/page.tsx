'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  getSovereigntyStatus,
  runSovereigntySelfTest,
  SovereigntyStatus,
  SovereigntyCheckResult,
  BlockedAttempt,
} from '../../lib/sovereignty-api';

/* =========================================================================
   Sovereignty Dashboard — Sprint 7
   Judge-visible, real-time sovereignty monitoring page.
   Pulls all data from the backend. NEVER shows optimistic assumptions.
   ========================================================================= */

export default function SovereigntyDashboard() {
  const [status, setStatus] = useState<SovereigntyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getSovereigntyStatus();
      setStatus(data);
      setLastRefresh(new Date().toLocaleTimeString());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchStatus]);

  const handleSelfTest = async () => {
    setTesting(true);
    try {
      const data = await runSovereigntySelfTest();
      setStatus(data);
      setLastRefresh(new Date().toLocaleTimeString());
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setTesting(false);
    }
  };

  const stateColor = (state: string) => {
    switch (state) {
      case 'READY': return '#00e676';
      case 'NOT_READY': return '#ff5252';
      case 'DEGRADED': return '#ffab40';
      default: return '#ff5252';
    }
  };

  const stateIcon = (state: string) => {
    switch (state) {
      case 'READY': return '🛡️';
      case 'NOT_READY': return '⚠️';
      case 'DEGRADED': return '🔶';
      default: return '❌';
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)',
      color: '#e2e8f0',
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      padding: '2rem',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <a href="/" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.875rem' }}>← Back to Workbench</a>
          <h1 style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            background: 'linear-gradient(135deg, #60a5fa, #a78bfa)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0,
          }}>
            🛡️ Sovereignty Dashboard
          </h1>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.8rem', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <input type="checkbox" checked={autoRefresh} onChange={() => setAutoRefresh(!autoRefresh)} style={{ accentColor: '#60a5fa' }} />
            Auto-refresh (5s)
          </label>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Last: {lastRefresh || '—'}</span>
          <button
            onClick={handleSelfTest}
            disabled={testing}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              border: '1px solid rgba(96, 165, 250, 0.3)',
              background: testing ? 'rgba(30, 41, 59, 0.5)' : 'rgba(96, 165, 250, 0.1)',
              color: '#60a5fa',
              cursor: testing ? 'wait' : 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            {testing ? '⏳ Running Self-Test...' : '🔄 Run Self-Test'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '1rem', marginBottom: '1.5rem', borderRadius: '0.75rem',
          background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5', fontSize: '0.875rem',
        }}>
          ⚠️ Connection Error: {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔄</div>
          Loading sovereignty status...
        </div>
      ) : status && (
        <>
          {/* Main State Card */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(20px)',
            border: `1px solid ${stateColor(status.state)}33`,
            borderRadius: '1rem',
            padding: '2rem',
            marginBottom: '1.5rem',
            textAlign: 'center',
            boxShadow: `0 0 40px ${stateColor(status.state)}11`,
          }}>
            <div style={{ fontSize: '4rem', marginBottom: '0.5rem' }}>{stateIcon(status.state)}</div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 800,
              color: stateColor(status.state),
              letterSpacing: '0.05em',
              marginBottom: '0.5rem',
            }}>
              SOVEREIGNTY: {status.state}
            </div>
            <div style={{ fontSize: '0.9rem', color: '#94a3b8', maxWidth: '600px', margin: '0 auto' }}>
              {status.detail}
            </div>
          </div>

          {/* Zero-Counter Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
            {[
              { label: 'External Connections', value: status.external_connections, icon: '🌐' },
              { label: 'External DNS Queries', value: status.external_dns_queries, icon: '🔍' },
              { label: 'Cloud API Calls', value: status.cloud_api_calls, icon: '☁️' },
            ].map((counter) => (
              <div key={counter.label} style={{
                background: 'rgba(15, 23, 42, 0.6)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(71, 85, 105, 0.3)',
                borderRadius: '0.75rem',
                padding: '1.5rem',
                textAlign: 'center',
              }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>{counter.icon}</div>
                <div style={{
                  fontSize: '2.5rem',
                  fontWeight: 800,
                  fontVariantNumeric: 'tabular-nums',
                  color: counter.value === 0 ? '#00e676' : counter.value === -1 ? '#ff5252' : '#ffab40',
                }}>
                  {counter.value === -1 ? '—' : counter.value}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>{counter.label}</div>
                <div style={{ fontSize: '0.7rem', color: counter.value === 0 ? '#00e676' : '#ff5252' }}>
                  Target: 0
                </div>
              </div>
            ))}
          </div>

          {/* Individual Checks */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(71, 85, 105, 0.3)',
            borderRadius: '0.75rem',
            padding: '1.5rem',
            marginBottom: '1.5rem',
          }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: '#e2e8f0' }}>
              Sovereignty Checks ({status.checks.filter(c => c.passed).length}/{status.checks.length} passed)
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {status.checks.map((check: SovereigntyCheckResult, i: number) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.75rem 1rem',
                  borderRadius: '0.5rem',
                  background: check.passed ? 'rgba(0, 230, 118, 0.05)' : 'rgba(255, 82, 82, 0.05)',
                  border: `1px solid ${check.passed ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 82, 82, 0.2)'}`,
                }}>
                  <span style={{ fontSize: '1.2rem' }}>{check.passed ? '✅' : '❌'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', fontFamily: 'monospace', color: check.passed ? '#00e676' : '#ff5252' }}>
                      {check.check_name}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.15rem' }}>
                      {check.detail}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Blocked Attempts Log */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(71, 85, 105, 0.3)',
            borderRadius: '0.75rem',
            padding: '1.5rem',
          }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: '#e2e8f0' }}>
              🚫 Blocked Attempt Log ({status.blocked_attempts.length} entries)
            </h2>
            {status.blocked_attempts.length === 0 ? (
              <div style={{ color: '#64748b', fontSize: '0.875rem', padding: '1rem', textAlign: 'center' }}>
                No blocked attempts recorded yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '300px', overflowY: 'auto' }}>
                {status.blocked_attempts.map((attempt: BlockedAttempt, i: number) => (
                  <div key={i} style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 2fr',
                    gap: '1rem',
                    padding: '0.6rem 0.8rem',
                    borderRadius: '0.375rem',
                    background: 'rgba(255, 82, 82, 0.05)',
                    border: '1px solid rgba(255, 82, 82, 0.1)',
                    fontSize: '0.8rem',
                    fontFamily: 'monospace',
                  }}>
                    <span style={{ color: '#fca5a5' }}>{attempt.source}</span>
                    <span style={{ color: '#ff5252' }}>→ {attempt.destination}</span>
                    <span style={{ color: '#94a3b8' }}>{attempt.reason}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
