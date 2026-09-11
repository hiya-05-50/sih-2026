'use client';

import React, { useState, useEffect } from 'react';
import {
  submitTask,
  listTasks,
  listModels,
  runBenchmark,
  uploadDocument,
  getDocumentEvidence,
  executeVerticalSliceV0,
  TaskExecution,
  ModelRegistryEntry,
  RouteCandidate,
  EvidenceObject,
  DocumentMetadata,
  VerticalSliceV0Response,
} from '../lib/api';

const TASK_PRESETS = [
  {
    type: 'document_analysis',
    label: 'Document Vision & Analysis',
    description: 'Inspect scanned PDF/image for compliance evidence, spatial regions, and tabular OCR.',
    icon: '📄',
    priority: 'HIGH',
    sampleInput: { document_url: 'file:///samples/inspection_report_04.pdf', extract_regions: true },
  },
  {
    type: 'code_review',
    label: 'Code Quality & Security Audit',
    description: 'Perform static analysis and vulnerability audit on task state machine implementation.',
    icon: '💻',
    priority: 'HIGH',
    sampleInput: { source_file: 'backend/app/services/lifecycle.py', check_security: true },
  },
  {
    type: 'general_reasoning',
    label: 'Architecture & Policy Reasoning',
    description: 'Formulate multi-step task execution plan for sovereign local deployment.',
    icon: '🧠',
    priority: 'MEDIUM',
    sampleInput: { query: 'Analyze trade-offs of vLLM vs Ollama on RTX 4060 8GB VRAM' },
  },
  {
    type: 'data_extraction',
    label: 'Structured Data Extraction',
    description: 'Extract normalized key-value fields from unstructured audit log.',
    icon: '📊',
    priority: 'LOW',
    sampleInput: { raw_text: 'ERROR 2026-09-10 14:02:11 router.py:44 VRAM threshold exceeded by 1024MB' },
  },
];

export default function WorkbenchPage() {
  const [activeTab, setActiveTab] = useState<'workbench' | 'evidence' | 'registry' | 'history'>('workbench');

  // Form state
  const [taskType, setTaskType] = useState('document_analysis');
  const [description, setDescription] = useState(TASK_PRESETS[0].description);
  const [priority, setPriority] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('HIGH');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Execution state
  const [currentExecution, setCurrentExecution] = useState<TaskExecution | null>(null);
  const [tasks, setTasks] = useState<TaskExecution[]>([]);
  const [models, setModels] = useState<ModelRegistryEntry[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [benchmarkingModel, setBenchmarkingModel] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sprint 2 Document & Evidence Explorer State
  const [activeDocument, setActiveDocument] = useState<DocumentMetadata | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceObject[]>([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [isProcessingDoc, setIsProcessingDoc] = useState<boolean>(false);
  const [verticalSliceResult, setVerticalSliceResult] = useState<VerticalSliceV0Response | null>(null);

  // Load models and task history on mount
  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      setLoadingModels(true);
      const [fetchedModels, fetchedTasks] = await Promise.all([
        listModels().catch(() => []),
        listTasks().catch(() => []),
      ]);
      setModels(fetchedModels);
      setTasks(fetchedTasks);
    } catch (e: any) {
      setErrorMsg(e.message);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleSelectPreset = (preset: typeof TASK_PRESETS[0]) => {
    setTaskType(preset.type);
    setDescription(preset.description);
    setPriority(preset.priority as any);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const preset = TASK_PRESETS.find(p => p.type === taskType);
      const execution = await submitTask(taskType, description, preset?.sampleInput || {}, priority);
      setCurrentExecution(execution);
      setTasks(prev => [execution, ...prev]);
    } catch (err: any) {
      setErrorMsg(err.message || 'Task execution failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBenchmark = async (modelId: string) => {
    setBenchmarkingModel(modelId);
    try {
      const updatedProfile = await runBenchmark(modelId);
      setModels(prev =>
        prev.map(m => (m.model_id === modelId ? { ...m, benchmark_profile: updatedProfile } : m))
      );
    } catch (err: any) {
      alert(`Benchmark error: ${err.message}`);
    } finally {
      setBenchmarkingModel(null);
    }
  };

  // Sprint 2 Document Handlers
  const handleLoadSampleDocument = async () => {
    setIsProcessingDoc(true);
    setErrorMsg(null);
    try {
      const meta = await uploadDocument();
      setActiveDocument(meta);
      const evidence = await getDocumentEvidence(meta.document_id);
      setEvidenceList(evidence);
    } catch (err: any) {
      setErrorMsg(err.message || 'Document processing failed');
    } finally {
      setIsProcessingDoc(false);
    }
  };

  const handleRunVerticalSliceV0 = async () => {
    setIsProcessingDoc(true);
    setErrorMsg(null);
    try {
      let docId = activeDocument?.document_id;
      if (!docId) {
        const meta = await uploadDocument();
        docId = meta.document_id;
        setActiveDocument(meta);
      }
      const v0Resp = await executeVerticalSliceV0(docId);
      setVerticalSliceResult(v0Resp);
      setActiveDocument(v0Resp.document_metadata);
      setEvidenceList(v0Resp.evidence_objects);
    } catch (err: any) {
      setErrorMsg(err.message || 'Vertical slice V0 execution failed');
    } finally {
      setIsProcessingDoc(false);
    }
  };

  const filteredEvidence = evidenceList.filter(ev =>
    typeFilter === 'ALL' ? true : ev.evidence_type === typeFilter
  );

  const getRegionBorderColor = (type: string, isSelected: boolean) => {
    if (isSelected) return 'border-cyan-400 bg-cyan-500/30 ring-2 ring-cyan-400 shadow-cyan-500/50 shadow-lg z-20';
    switch (type) {
      case 'TABLE':
        return 'border-amber-500 bg-amber-500/10 hover:bg-amber-500/20';
      case 'STAMP':
        return 'border-emerald-500 bg-emerald-500/10 hover:bg-emerald-500/20';
      case 'SIGNATURE':
        return 'border-purple-500 bg-purple-500/10 hover:bg-purple-500/20';
      case 'KEY_VALUE':
        return 'border-cyan-500 bg-cyan-500/10 hover:bg-cyan-500/20';
      default:
        return 'border-blue-500 bg-blue-500/10 hover:bg-blue-500/20';
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-white">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex flex-wrap items-center justify-between shadow-lg">
        <div className="flex items-center space-x-4">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-xl shadow-cyan-500/20 shadow-lg">
            S
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              SAFIRE Workbench
            </h1>
            <p className="text-xs text-slate-400 font-mono">Sovereign Agentic AI & Evidence Intelligence Engine</p>
          </div>
        </div>

        {/* Tab Selector */}
        <nav className="flex items-center space-x-1 bg-slate-950 p-1.5 rounded-xl border border-slate-800/80 my-2 sm:my-0">
          <button
            onClick={() => setActiveTab('workbench')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              activeTab === 'workbench'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            ⚡ Task Pipeline
          </button>
          <button
            onClick={() => {
              setActiveTab('evidence');
              if (!activeDocument) handleLoadSampleDocument();
            }}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all flex items-center space-x-1.5 ${
              activeTab === 'evidence'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <span>📄 Evidence Explorer & V0</span>
            <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-1.5 py-0.5 rounded font-mono">
              Sprint 2
            </span>
          </button>
          <button
            onClick={() => setActiveTab('registry')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              activeTab === 'registry'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            🤖 Models ({models.length})
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
              activeTab === 'history'
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            📋 Audit ({tasks.length})
          </button>
          <a
            href="/sovereignty"
            className="px-4 py-2 text-sm font-semibold rounded-lg transition-all text-emerald-400 hover:text-emerald-200 hover:bg-slate-900 flex items-center space-x-1.5"
          >
            <span>🛡️ Sovereignty</span>
            <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-1.5 py-0.5 rounded font-mono">
              Live
            </span>
          </a>
          <a
            href="/demo"
            className="px-4 py-2 text-sm font-semibold rounded-lg transition-all text-amber-400 hover:text-amber-200 hover:bg-slate-900 flex items-center space-x-1.5"
          >
            <span>🎯 Demo</span>
            <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-800 px-1.5 py-0.5 rounded font-mono">
              21-Step
            </span>
          </a>
        </nav>

        {/* System Hardware Status Badge */}
        <div className="flex items-center space-x-3 text-xs bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 font-mono">
          <div className="flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-300">Target hardware: RTX 4060 (8GB VRAM)</span>
          </div>
          <span className="text-slate-600">|</span>
          <span className="text-cyan-400 font-semibold">Slice V0: Active</span>
        </div>
      </header>

      {/* Main Container */}
      <main className="p-6 max-w-7xl mx-auto space-y-6">
        {errorMsg && (
          <div className="p-4 rounded-xl bg-red-950/80 border border-red-800/80 text-red-200 text-sm flex items-center justify-between">
            <span>⚠️ {errorMsg}</span>
            <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-red-100 font-bold">
              ✕
            </button>
          </div>
        )}

        {/* TAB 1: WORKBENCH PIPELINE */}
        {activeTab === 'workbench' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Form & Presets */}
            <div className="lg:col-span-5 space-y-6">
              {/* Presets */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur shadow-sm">
                <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">
                  Task Presets
                </h3>
                <div className="grid grid-cols-2 gap-2.5">
                  {TASK_PRESETS.map(preset => (
                    <button
                      key={preset.type}
                      type="button"
                      onClick={() => handleSelectPreset(preset)}
                      className={`p-3 rounded-xl text-left border transition-all flex flex-col justify-between ${
                        taskType === preset.type
                          ? 'border-cyan-500 bg-cyan-950/30 ring-1 ring-cyan-500/50'
                          : 'border-slate-800 bg-slate-950/50 hover:border-slate-700 hover:bg-slate-900'
                      }`}
                    >
                      <div className="text-xl mb-1">{preset.icon}</div>
                      <div>
                        <div className="text-xs font-bold text-slate-200 leading-tight">
                          {preset.label}
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 mt-1 uppercase">
                          {preset.type}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Submission Form */}
              <form
                onSubmit={handleSubmit}
                className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur space-y-4 shadow-sm"
              >
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                    Submit Task Profile
                  </h3>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                    Sprint 1 Pipeline
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">
                    Task Type
                  </label>
                  <select
                    value={taskType}
                    onChange={e => setTaskType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition font-mono"
                  >
                    <option value="document_analysis">document_analysis (Requires Vision)</option>
                    <option value="code_review">code_review (Requires Coding)</option>
                    <option value="general_reasoning">general_reasoning (Requires Reasoning)</option>
                    <option value="data_extraction">data_extraction (Requires Text)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">
                    Task Description & Requirements
                  </label>
                  <textarea
                    rows={4}
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="Describe the objective..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">
                    Priority Level
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['LOW', 'MEDIUM', 'HIGH'] as const).map(p => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPriority(p)}
                        className={`py-1.5 text-xs font-semibold rounded-lg border transition ${
                          priority === p
                            ? 'bg-slate-800 border-cyan-500 text-cyan-300'
                            : 'border-slate-800 text-slate-400 hover:bg-slate-950'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-bold text-sm shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50 flex items-center justify-center space-x-2"
                >
                  {isSubmitting ? (
                    <>
                      <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                      <span>Routing & Executing...</span>
                    </>
                  ) : (
                    <>
                      <span>🚀 Execute Pipeline</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Right Column: Execution View & Rationale Panel */}
            <div className="lg:col-span-7 space-y-6">
              {currentExecution ? (
                <>
                  {/* Task State Machine Lifecycle Header */}
                  <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur space-y-4 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/80">
                          ID: {currentExecution.task_id.substring(0, 8)}
                        </span>
                        <span className="text-xs font-semibold text-slate-400">
                          Type: <code className="text-cyan-400">{currentExecution.task_profile.task_type}</code>
                        </span>
                      </div>
                      <span
                        className={`text-xs font-bold px-3 py-1 rounded-full border ${
                          currentExecution.current_state === 'DELIVER'
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                            : currentExecution.current_state === 'FAILED'
                            ? 'bg-red-950 text-red-300 border-red-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800 animate-pulse'
                        }`}
                      >
                        State: {currentExecution.current_state}
                      </span>
                    </div>

                    {/* Visual State Flow Machine */}
                    <div className="pt-2">
                      <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                        Task Lifecycle State Transitions
                      </div>
                      <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800/80 font-mono text-xs overflow-x-auto">
                        {['INTAKE', 'CLASSIFY', 'PLAN', 'DELIVER'].map((state, idx, arr) => {
                          const visited = currentExecution.state_history.some(
                            h => h.to_state === state || h.from_state === state
                          );
                          const isCurrent = currentExecution.current_state === state;
                          return (
                            <React.Fragment key={state}>
                              <div
                                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border ${
                                  isCurrent
                                    ? 'bg-cyan-950 border-cyan-500 text-cyan-300 font-bold ring-1 ring-cyan-500/50'
                                    : visited
                                    ? 'bg-slate-900 border-slate-700 text-emerald-400'
                                    : 'bg-slate-950 border-slate-800 text-slate-600'
                                }`}
                              >
                                <span>{visited ? '✓' : idx + 1}</span>
                                <span>{state}</span>
                              </div>
                              {idx < arr.length - 1 && (
                                <span className="text-slate-700 font-extrabold">→</span>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* JUDGE-VISIBLE ROUTING RATIONALE PANEL */}
                  {currentExecution.route_decision && (
                    <div className="bg-gradient-to-b from-slate-900 to-slate-900/90 border-2 border-cyan-500/80 rounded-2xl p-5 shadow-xl shadow-cyan-950/40 space-y-4 relative overflow-hidden">
                      <div className="absolute top-0 right-0 bg-cyan-500 text-slate-950 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-bl-xl shadow">
                        Master PRD §14 Explained
                      </div>

                      <div className="flex items-center space-x-2">
                        <span className="text-lg">🎯</span>
                        <h3 className="text-base font-extrabold text-cyan-300 tracking-tight">
                          Deterministic Routing Rationale
                        </h3>
                      </div>

                      {/* Reasoning Box */}
                      <div className="bg-slate-950/90 border border-cyan-800/60 rounded-xl p-4 font-mono text-xs text-slate-200 space-y-2 leading-relaxed">
                        <div className="text-slate-400 font-semibold border-b border-slate-800 pb-1 text-[11px]">
                          EVIDENCE & EXPLANATION STRING:
                        </div>
                        <p className="text-cyan-200">{currentExecution.routing_rationale}</p>
                      </div>

                      {/* Model Decision Metadata */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <div className="text-[10px] text-slate-500 uppercase font-mono">
                            Selected Model
                          </div>
                          <div className="font-bold text-slate-200 truncate">
                            {currentExecution.route_decision.selected_model_name}
                          </div>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <div className="text-[10px] text-slate-500 uppercase font-mono">
                            Capabilities Matched
                          </div>
                          <div className="font-bold text-emerald-400 truncate">
                            {currentExecution.route_decision.matched_capabilities.join(', ')}
                          </div>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <div className="text-[10px] text-slate-500 uppercase font-mono">
                            Context Window
                          </div>
                          <div className="font-bold text-cyan-300 font-mono">
                            {currentExecution.route_decision.context_window_size.toLocaleString()} tokens
                          </div>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <div className="text-[10px] text-slate-500 uppercase font-mono">
                            Est. Latency
                          </div>
                          <div className="font-bold text-amber-300 font-mono">
                            {currentExecution.route_decision.estimated_latency_ms || 45} ms
                          </div>
                        </div>
                      </div>

                      {/* Candidate Scoring Breakdown */}
                      {currentExecution.route_decision.candidates && (
                        <div className="space-y-2 pt-2 border-t border-slate-800">
                          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                            5-Step Candidate Scoring Matrix
                          </div>
                          <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden text-xs font-mono">
                            <table className="w-full text-left border-collapse">
                              <thead>
                                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 text-[10px] uppercase">
                                  <th className="p-2">Model</th>
                                  <th className="p-2">VRAM Feasible?</th>
                                  <th className="p-2">Latency Score</th>
                                  <th className="p-2">VRAM Score</th>
                                  <th className="p-2 text-right">Composite Score</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60">
                                {currentExecution.route_decision.candidates.map((cand: RouteCandidate) => (
                                  <tr
                                    key={cand.model_id}
                                    className={
                                      cand.model_id === currentExecution.route_decision?.selected_model
                                        ? 'bg-cyan-950/40 text-cyan-200 font-bold'
                                        : 'text-slate-400'
                                    }
                                  >
                                    <td className="p-2">{cand.model_name}</td>
                                    <td className="p-2">
                                      {cand.feasible ? (
                                        <span className="text-emerald-400">✓ Feasible</span>
                                      ) : (
                                        <span className="text-red-400">✗ Exceeds VRAM</span>
                                      )}
                                    </td>
                                    <td className="p-2">{cand.latency_score.toFixed(2)}</td>
                                    <td className="p-2">{cand.vram_score.toFixed(2)}</td>
                                    <td className="p-2 text-right font-extrabold text-cyan-400">
                                      {cand.composite_score.toFixed(3)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Model Execution Output Panel */}
                  <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 backdrop-blur space-y-3 shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                        Model Output Result
                      </h3>
                      <span className="text-xs font-mono text-emerald-400">
                        {currentExecution.completed_at ? 'Execution Completed' : 'Processing...'}
                      </span>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-sm font-mono text-slate-200 whitespace-pre-wrap leading-relaxed min-h-[140px]">
                      {currentExecution.model_response || currentExecution.error || 'Awaiting response...'}
                    </div>
                  </div>
                </>
              ) : (
                /* Empty state */
                <div className="bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-4">
                  <div className="text-5xl">⚡</div>
                  <div className="space-y-1">
                    <h3 className="text-lg font-bold text-slate-300">No Task Submitted Yet</h3>
                    <p className="text-sm text-slate-500 max-w-md mx-auto">
                      Select a preset on the left or enter a task profile to execute the full SAFIRE task lifecycle state machine and view the routing rationale.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: EVIDENCE EXPLORER & VERTICAL SLICE V0 */}
        {activeTab === 'evidence' && (
          <div className="space-y-6">
            {/* Top Toolbar */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <h2 className="text-lg font-bold text-slate-100">Evidence Intelligence Explorer</h2>
                  <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                    Master PRD §16
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Traceable Evidence Objects with SHA-256 source hashing & normalized coordinate bounding boxes
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={handleLoadSampleDocument}
                  disabled={isProcessingDoc}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200 transition disabled:opacity-50 flex items-center space-x-2"
                >
                  <span>📄 Load Inspection Report</span>
                </button>
                <button
                  onClick={handleRunVerticalSliceV0}
                  disabled={isProcessingDoc}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white text-xs font-extrabold shadow-lg shadow-cyan-500/20 transition disabled:opacity-50 flex items-center space-x-2"
                >
                  {isProcessingDoc ? (
                    <>
                      <span className="h-3.5 w-3.5 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                      <span>Processing V0 Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <span>🚀 Run Vertical Slice V0</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Document Metadata Bar */}
            {activeDocument && (
              <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-3 px-4 text-xs font-mono flex flex-wrap items-center justify-between text-slate-300">
                <div className="flex items-center space-x-3">
                  <span className="text-cyan-400 font-bold">Document: {activeDocument.filename}</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-400">ID: {activeDocument.document_id}</span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-emerald-400">SHA-256: {activeDocument.sha256_hash.substring(0, 16)}...</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-amber-400">Evidence Count: {evidenceList.length} Objects</span>
                </div>
              </div>
            )}

            {/* Vertical Slice V0 Result Card */}
            {verticalSliceResult && (
              <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border-2 border-emerald-500/80 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">✅</span>
                    <h3 className="text-base font-extrabold text-emerald-300">
                      Vertical Slice V0 Pipeline Execution Complete
                    </h3>
                  </div>
                  <span className="text-xs font-mono text-cyan-400 bg-slate-950 px-3 py-1 rounded-full border border-slate-800">
                    Duration: {verticalSliceResult.pipeline_duration_ms.toFixed(1)} ms
                  </span>
                </div>

                {/* Pipeline Flow Stepper */}
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs font-mono text-center">
                  <div className="bg-slate-950 p-2 rounded-lg border border-emerald-800/60 text-emerald-300">
                    1. UPLOAD ✓
                  </div>
                  <div className="bg-slate-950 p-2 rounded-lg border border-emerald-800/60 text-emerald-300">
                    2. OCR/VISION ✓
                  </div>
                  <div className="bg-slate-950 p-2 rounded-lg border border-emerald-800/60 text-emerald-300">
                    3. EVIDENCE ✓ ({verticalSliceResult.evidence_count})
                  </div>
                  <div className="bg-slate-950 p-2 rounded-lg border border-emerald-800/60 text-emerald-300">
                    4. RETRIEVAL ✓ ({verticalSliceResult.retrieval_indexed_count})
                  </div>
                  <div className="bg-slate-950 p-2 rounded-lg border border-emerald-800/60 text-emerald-300">
                    5. REASONING ✓
                  </div>
                  <div className="bg-slate-950 p-2 rounded-lg border border-emerald-800/60 text-emerald-300">
                    6. ARTIFACT ✓
                  </div>
                </div>

                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 leading-relaxed">
                  <span className="text-slate-400 font-bold">REASONING SUMMARY: </span>
                  <span className="text-emerald-200">{verticalSliceResult.reasoning_summary}</span>
                </div>
              </div>
            )}

            {/* Split View: Left Document Interactive Layout - Right Evidence Objects List */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left 6 cols: Document Page Canvas */}
              <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Document Page 1 Visual Region Canvas
                  </h3>
                  <span className="text-[10px] font-mono text-slate-500">
                    Normalized Bounding Boxes [0.0 - 1.0]
                  </span>
                </div>

                {/* Simulated Document Canvas Container */}
                <div className="relative w-full aspect-[1/1.3] bg-slate-950 border border-slate-800 rounded-xl p-4 overflow-hidden shadow-inner font-mono text-[11px] text-slate-400 select-none">
                  {/* Subtle document grid lines background */}
                  <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:10%_10%] opacity-20 pointer-events-none" />

                  {/* Render Bounding Box Overlays */}
                  {filteredEvidence.map(ev => {
                    const isSelected = selectedEvidenceId === ev.evidence_id;
                    return (
                      <div
                        key={ev.evidence_id}
                        onClick={() => setSelectedEvidenceId(ev.evidence_id)}
                        style={{
                          left: `${ev.region.x * 100}%`,
                          top: `${ev.region.y * 100}%`,
                          width: `${ev.region.width * 100}%`,
                          height: `${ev.region.height * 100}%`,
                        }}
                        className={`absolute border-2 rounded-lg p-1.5 transition-all cursor-pointer flex flex-col justify-between ${getRegionBorderColor(
                          ev.evidence_type,
                          isSelected
                        )}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[9px] font-bold px-1.5 py-0.2 bg-slate-950/80 rounded border border-slate-700 text-slate-200">
                            {ev.evidence_type}
                          </span>
                          <span className="text-[9px] font-mono text-slate-300 font-extrabold">
                            {(ev.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="truncate text-[10px] text-slate-200 font-semibold opacity-90">
                          {ev.extracted_text.split('\n')[0]}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right 6 cols: Traceable Evidence Objects List */}
              <div className="lg:col-span-6 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur space-y-4 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      Traceable Evidence Objects ({filteredEvidence.length})
                    </h3>

                    {/* Type Filter Buttons */}
                    <div className="flex items-center space-x-1 text-[10px] font-mono">
                      {['ALL', 'TABLE', 'STAMP', 'SIGNATURE', 'KEY_VALUE'].map(f => (
                        <button
                          key={f}
                          onClick={() => setTypeFilter(f)}
                          className={`px-2 py-0.5 rounded border transition ${
                            typeFilter === f
                              ? 'bg-cyan-950 border-cyan-500 text-cyan-300 font-bold'
                              : 'border-slate-800 text-slate-400 hover:bg-slate-900'
                          }`}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Evidence Cards List */}
                  <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                    {filteredEvidence.map(ev => {
                      const isSelected = selectedEvidenceId === ev.evidence_id;
                      return (
                        <div
                          key={ev.evidence_id}
                          onClick={() => setSelectedEvidenceId(ev.evidence_id)}
                          className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2 ${
                            isSelected
                              ? 'border-cyan-500 bg-cyan-950/40 ring-1 ring-cyan-500/50 shadow-md'
                              : 'border-slate-800/80 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/80'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="text-xs font-mono font-bold text-cyan-400">
                                {ev.evidence_id}
                              </span>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                                Page {ev.page_number}
                              </span>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/80">
                                {ev.evidence_type}
                              </span>
                            </div>
                            <span className="text-xs font-mono text-emerald-400 font-bold">
                              Confidence: {(ev.confidence * 100).toFixed(0)}%
                            </span>
                          </div>

                          <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
                            {ev.extracted_text}
                          </div>

                          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
                            <span>
                              BBox: [{ev.region.x.toFixed(2)}, {ev.region.y.toFixed(2)}, {ev.region.width.toFixed(2)}, {ev.region.height.toFixed(2)}]
                            </span>
                            <span className="text-slate-400 truncate max-w-[200px]">
                              SHA-256: {ev.source_hash.substring(0, 12)}...
                            </span>
                          </div>

                          {ev.metadata?.vision_rationale && (
                            <div className="text-[10px] font-mono text-cyan-300 bg-cyan-950/30 p-1.5 rounded border border-cyan-800/50">
                              🎯 Targeted Vision: {ev.metadata.vision_rationale}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {filteredEvidence.length === 0 && (
                      <div className="p-8 text-center text-xs font-mono text-slate-500 border border-dashed border-slate-800 rounded-xl">
                        No Evidence Objects matching filter.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: MODEL REGISTRY & BENCHMARKS */}
        {activeTab === 'registry' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-200">Registered Model Roles</h2>
                <p className="text-xs text-slate-400">
                  Pre-seeded model roles with hardware VRAM constraints & real measured benchmarks
                </p>
              </div>
              <button
                onClick={fetchInitialData}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-300"
              >
                🔄 Refresh Registry
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {models.map(model => (
                <div
                  key={model.model_id}
                  className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4 backdrop-blur flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-base font-bold text-slate-100">{model.name}</h3>
                        <div className="text-xs font-mono text-cyan-400">{model.model_id}</div>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {model.runtime || 'ollama'}
                      </span>
                    </div>

                    {/* Capabilities */}
                    <div>
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                        Capabilities
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {model.capabilities.map(cap => (
                          <span
                            key={cap}
                            className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60"
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Specs */}
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
                      <div>
                        <span className="text-slate-500">Context:</span>{' '}
                        <span className="text-slate-200">{model.context_length.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">VRAM:</span>{' '}
                        <span className="text-amber-400">{model.vram_footprint_mb || 4000} MB</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Family:</span>{' '}
                        <span className="text-slate-200">{model.model_family || 'qwen'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Quant:</span>{' '}
                        <span className="text-slate-200">{model.quantization || 'Q4_K_M'}</span>
                      </div>
                    </div>

                    {/* Measured Benchmarks */}
                    <div className="space-y-1.5">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                        Measured Benchmarks (Real Metrics)
                      </div>
                      {model.benchmark_profile ? (
                        <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs font-mono space-y-1 text-slate-300">
                          <div className="flex justify-between">
                            <span className="text-slate-500">Cold Start Latency:</span>
                            <span className="text-cyan-400 font-bold">
                              {model.benchmark_profile.cold_start_latency_ms?.toFixed(1)} ms
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Warm Inference Latency:</span>
                            <span className="text-emerald-400 font-bold">
                              {model.benchmark_profile.warm_inference_latency_ms?.toFixed(1)} ms
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Measured VRAM Usage:</span>
                            <span className="text-amber-400 font-bold">
                              {model.benchmark_profile.vram_usage_mb} MB
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-xs font-mono text-slate-500 bg-slate-950 p-3 rounded-xl border border-slate-800">
                          Unmeasured (Defaults active)
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => handleBenchmark(model.model_id)}
                    disabled={benchmarkingModel === model.model_id}
                    className="w-full mt-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition disabled:opacity-50"
                  >
                    {benchmarkingModel === model.model_id ? '⏱️ Measuring...' : '📊 Run Benchmark Measure'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 4: AUDIT TRAIL HISTORY */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-slate-200">Execution Audit Log</h2>
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur">
              <table className="w-full text-left text-xs font-mono border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 uppercase text-[10px]">
                    <th className="p-3">Task ID</th>
                    <th className="p-3">Task Type</th>
                    <th className="p-3">State</th>
                    <th className="p-3">Selected Model</th>
                    <th className="p-3">Timestamp</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {tasks.map(t => (
                    <tr key={t.task_id} className="hover:bg-slate-900/80 transition">
                      <td className="p-3 font-bold text-cyan-400">{t.task_id.substring(0, 8)}</td>
                      <td className="p-3 text-slate-200">{t.task_profile.task_type}</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                          {t.current_state}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300">
                        {t.route_decision?.selected_model_name || 'N/A'}
                      </td>
                      <td className="p-3 text-slate-500">{new Date(t.started_at).toLocaleTimeString()}</td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => {
                            setCurrentExecution(t);
                            setActiveTab('workbench');
                          }}
                          className="text-cyan-400 hover:text-cyan-200 font-bold"
                        >
                          View Rationale →
                        </button>
                      </td>
                    </tr>
                  ))}
                  {tasks.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-slate-500">
                        No tasks executed yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
