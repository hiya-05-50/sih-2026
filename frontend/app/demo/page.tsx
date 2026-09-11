'use client';

import React, { useState, useEffect } from 'react';
import {
  runDemoSequence,
  getLatestDemoResult,
  getAllDemoResults,
  getTraceabilityReport,
  DemoSequenceResult,
  DemoStepResult,
  TraceabilityReport,
} from '../../lib/demo-api';

/* =========================================================================
   Demo Command Center — Sprint 7
   Judge-facing demo control panel. Run and monitor the full 21-step
   judge demo sequence. View traceability sign-off.
   ========================================================================= */

export default function DemoCommandCenter() {
  const [activeTab, setActiveTab] = useState<'sequence' | 'traceability' | 'history'>('sequence');
  const [currentResult, setCurrentResult] = useState<DemoSequenceResult | null>(null);
  const [allResults, setAllResults] = useState<DemoSequenceResult[]>([]);
  const [traceability, setTraceability] = useState<TraceabilityReport | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadExisting();
  }, []);

  const loadExisting = async () => {
    try {
      const [latest, all, trace] = await Promise.allSettled([
        getLatestDemoResult(),
        getAllDemoResults(),
        getTraceabilityReport(),
      ]);
      if (latest.status === 'fulfilled') setCurrentResult(latest.value);
      if (all.status === 'fulfilled') setAllResults(all.value);
      if (trace.status === 'fulfilled') setTraceability(trace.value);
    } catch { /* ignore */ }
  };

  const handleRunSequence = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await runDemoSequence();
      setCurrentResult(result);
      setAllResults(prev => [...prev, result]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const stepStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS': return '✅';
      case 'FAIL': return '❌';
      case 'SKIP': return '⏭️';
      default: return '⏳';
    }
  };

  const stepStatusColor = (status: string) => {
    switch (status) {
      case 'PASS': return '#00e676';
      case 'FAIL': return '#ff5252';
      case 'SKIP': return '#ffab40';
      default: return '#64748b';
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
            background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0,
          }}>
            🎯 Demo Command Center
          </h1>
        </div>
        <button
          onClick={handleRunSequence}
          disabled={running}
          style={{
            padding: '0.75rem 1.5rem',
            borderRadius: '0.75rem',
            border: 'none',
            background: running
              ? 'linear-gradient(135deg, #374151, #4b5563)'
              : 'linear-gradient(135deg, #f59e0b, #ef4444)',
            color: '#fff',
            cursor: running ? 'wait' : 'pointer',
            fontSize: '1rem',
            fontWeight: 700,
            letterSpacing: '0.02em',
            transition: 'all 0.3s',
            boxShadow: running ? 'none' : '0 4px 20px rgba(245, 158, 11, 0.3)',
          }}
        >
          {running ? '⏳ Running 21-Step Sequence...' : '🚀 Run Full Demo Sequence'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '1rem', marginBottom: '1.5rem', borderRadius: '0.75rem',
          background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5', fontSize: '0.875rem',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Tab Bar */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {([
          { key: 'sequence', label: '📋 Demo Sequence' },
          { key: 'traceability', label: '✅ Traceability' },
          { key: 'history', label: '📜 Run History' },
        ] as const).map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '0.6rem 1.2rem',
              borderRadius: '0.5rem',
              border: `1px solid ${activeTab === tab.key ? 'rgba(245, 158, 11, 0.4)' : 'rgba(71, 85, 105, 0.3)'}`,
              background: activeTab === tab.key ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
              color: activeTab === tab.key ? '#fbbf24' : '#94a3b8',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sequence Tab */}
      {activeTab === 'sequence' && (
        <>
          {currentResult ? (
            <>
              {/* Summary Bar */}
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem',
              }}>
                {[
                  { label: 'Status', value: currentResult.overall_status, color: currentResult.overall_status === 'PASS' ? '#00e676' : '#ff5252' },
                  { label: 'Passed', value: `${currentResult.passed_steps}/21`, color: '#00e676' },
                  { label: 'Failed', value: `${currentResult.failed_steps}`, color: currentResult.failed_steps > 0 ? '#ff5252' : '#00e676' },
                  { label: 'Duration', value: `${(currentResult.total_duration_ms / 1000).toFixed(1)}s`, color: '#60a5fa' },
                ].map(card => (
                  <div key={card.label} style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(71, 85, 105, 0.3)',
                    borderRadius: '0.75rem',
                    padding: '1.25rem',
                    textAlign: 'center',
                  }}>
                    <div style={{ fontSize: '1.75rem', fontWeight: 800, color: card.color, fontVariantNumeric: 'tabular-nums' }}>
                      {card.value}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>{card.label}</div>
                  </div>
                ))}
              </div>

              {/* Step List */}
              <div style={{
                background: 'rgba(15, 23, 42, 0.6)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(71, 85, 105, 0.3)',
                borderRadius: '0.75rem',
                padding: '1.5rem',
              }}>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>
                  21-Step Judge Demo — Run {currentResult.run_id}
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {currentResult.steps.map((step: DemoStepResult) => (
                    <div key={step.step_number} style={{
                      display: 'grid',
                      gridTemplateColumns: '2rem 1fr 5rem 5rem',
                      gap: '0.75rem',
                      alignItems: 'center',
                      padding: '0.6rem 0.8rem',
                      borderRadius: '0.375rem',
                      background: `${stepStatusColor(step.status)}08`,
                      border: `1px solid ${stepStatusColor(step.status)}22`,
                      fontSize: '0.85rem',
                    }}>
                      <span style={{ fontWeight: 700, color: '#64748b', fontVariantNumeric: 'tabular-nums' }}>
                        {step.step_number}
                      </span>
                      <div>
                        <span style={{ fontWeight: 600 }}>{step.step_name}</span>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.1rem' }}>
                          {step.detail.substring(0, 120)}{step.detail.length > 120 ? '...' : ''}
                        </div>
                      </div>
                      <span style={{
                        color: stepStatusColor(step.status),
                        fontWeight: 700,
                        textAlign: 'center',
                      }}>
                        {stepStatusIcon(step.status)} {step.status}
                      </span>
                      <span style={{ color: '#64748b', fontFamily: 'monospace', fontSize: '0.75rem', textAlign: 'right' }}>
                        {step.duration_ms.toFixed(0)}ms
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(71, 85, 105, 0.3)',
              borderRadius: '0.75rem',
              padding: '4rem',
              textAlign: 'center',
              color: '#64748b',
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎯</div>
              <div style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No demo sequence has been run yet.</div>
              <div style={{ fontSize: '0.875rem' }}>Click &quot;Run Full Demo Sequence&quot; to execute all 21 judge demo steps.</div>
            </div>
          )}
        </>
      )}

      {/* Traceability Tab */}
      {activeTab === 'traceability' && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(71, 85, 105, 0.3)',
          borderRadius: '0.75rem',
          padding: '1.5rem',
        }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>
            PRD §41 Traceability Sign-Off
          </h2>
          {traceability ? (
            <>
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem',
              }}>
                <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(0, 230, 118, 0.05)', borderRadius: '0.5rem' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: '#00e676' }}>{traceability.implemented_count}</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Implemented</div>
                </div>
                <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255, 171, 64, 0.05)', borderRadius: '0.5rem' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ffab40' }}>{traceability.partial_count}</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Partial</div>
                </div>
                <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255, 82, 82, 0.05)', borderRadius: '0.5rem' }}>
                  <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ff5252' }}>{traceability.pending_count}</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Pending</div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {traceability.requirements.map(req => (
                  <div key={req.requirement_id} style={{
                    padding: '0.75rem 1rem',
                    borderRadius: '0.5rem',
                    background: req.status === 'IMPLEMENTED' ? 'rgba(0, 230, 118, 0.05)' : 'rgba(255, 171, 64, 0.05)',
                    border: `1px solid ${req.status === 'IMPLEMENTED' ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 171, 64, 0.2)'}`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                      <span style={{ fontWeight: 800, color: '#60a5fa', fontFamily: 'monospace' }}>{req.requirement_id}</span>
                      <span style={{ fontWeight: 600 }}>{req.description}</span>
                      <span style={{
                        marginLeft: 'auto',
                        fontSize: '0.75rem',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '0.25rem',
                        background: req.status === 'IMPLEMENTED' ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 171, 64, 0.15)',
                        color: req.status === 'IMPLEMENTED' ? '#00e676' : '#ffab40',
                        fontWeight: 700,
                      }}>
                        {req.status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{req.evidence_detail}</div>
                    {req.demo_step_numbers.length > 0 && (
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                        Demo steps: {req.demo_step_numbers.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem' }}>
              Loading traceability report...
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(71, 85, 105, 0.3)',
          borderRadius: '0.75rem',
          padding: '1.5rem',
        }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>
            Run History ({allResults.length} runs)
          </h2>
          {allResults.length === 0 ? (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem' }}>No runs recorded yet.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {allResults.slice().reverse().map((run, i) => (
                <div key={run.run_id} style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 5rem 5rem 5rem 7rem',
                  gap: '1rem',
                  alignItems: 'center',
                  padding: '0.75rem 1rem',
                  borderRadius: '0.5rem',
                  background: run.overall_status === 'PASS' ? 'rgba(0, 230, 118, 0.05)' : 'rgba(255, 82, 82, 0.05)',
                  border: `1px solid ${run.overall_status === 'PASS' ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 82, 82, 0.2)'}`,
                  fontSize: '0.85rem',
                }}>
                  <span style={{ fontFamily: 'monospace', color: '#60a5fa' }}>{run.run_id}</span>
                  <span style={{ color: run.overall_status === 'PASS' ? '#00e676' : '#ff5252', fontWeight: 700, textAlign: 'center' }}>
                    {run.overall_status}
                  </span>
                  <span style={{ color: '#94a3b8', textAlign: 'center' }}>{run.passed_steps}/21</span>
                  <span style={{ color: '#64748b', textAlign: 'center' }}>{(run.total_duration_ms / 1000).toFixed(1)}s</span>
                  <span style={{ color: '#64748b', fontSize: '0.75rem', textAlign: 'right' }}>
                    {run.started_at ? new Date(run.started_at).toLocaleTimeString() : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
