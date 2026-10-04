import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  api,
  type GenericNode,
  type TraceListItem,
  type TraceDagResponse,
  type ReplayResponse,
} from './api';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock,
  CornerDownRight,
  Database,
  Eye,
  GitBranch,
  Layers,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Server,
  Terminal,
  User,
  XCircle,
  Zap,
} from 'lucide-react';

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatTimeAgo(dateStr: string) {
  if (!dateStr) return '—';
  try {
    const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
}

// ── Dynamic Node Form Generator ──────────────────────────────────────────────

function DynamicInputForm({
  inputs,
  onChange,
}: {
  inputs: Record<string, any>;
  onChange: (updated: Record<string, any>) => void;
}) {
  const keys = Object.keys(inputs || {});

  if (keys.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: 12, padding: '8px 0' }}>
        No input parameters recorded for this span.
      </div>
    );
  }

  const handleFieldChange = (key: string, rawVal: string) => {
    let parsed: any = rawVal;
    try {
      parsed = JSON.parse(rawVal);
    } catch {
      parsed = rawVal;
    }
    onChange({ ...inputs, [key]: parsed });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {keys.map((k) => {
        const val = inputs[k];
        const isComplex = typeof val === 'object' && val !== null;
        const displayVal = isComplex ? JSON.stringify(val, null, 2) : String(val ?? '');

        return (
          <div key={k}>
            <label
              style={{
                display: 'block',
                fontSize: 11,
                color: 'var(--text-muted)',
                marginBottom: 4,
                fontFamily: 'monospace',
                fontWeight: 600,
              }}
            >
              param: {k}
            </label>
            {isComplex || displayVal.length > 50 ? (
              <textarea
                value={displayVal}
                onChange={(e) => handleFieldChange(k, e.target.value)}
                rows={Math.min(displayVal.split('\n').length + 1, 6)}
                style={{ width: '100%', padding: '8px 10px', fontSize: 11, fontFamily: 'monospace' }}
              />
            ) : (
              <input
                value={displayVal}
                onChange={(e) => handleFieldChange(k, e.target.value)}
                style={{ width: '100%', padding: '6px 10px', fontSize: 11, fontFamily: 'monospace' }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main App Root ───────────────────────────────────────────────────────────

export default function App() {
  // Global Navigation
  const [project, setProject] = useState('Universal Execution Traces');
  const [searchQuery, setSearchQuery] = useState('');
  const [backendStatus, setBackendStatus] = useState<'unknown' | 'online' | 'offline'>('unknown');

  // Pane A: Trace List
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | 'failed' | 'success'>('all');
  const [loadingTraces, setLoadingTraces] = useState(false);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);

  // Pane B: Active DAG Data
  const [activeDag, setActiveDag] = useState<TraceDagResponse | null>(null);
  const [loadingDag, setLoadingDag] = useState(false);
  const [activeDiagnosis, setActiveDiagnosis] = useState<{
    status: string;
    failure_type: string | null;
    root_cause: { step_id: string | null; name: string | null; error: string | null } | null;
    evidence: Record<string, unknown>;
    explanation?: string;
  } | null>(null);

  // Pane C: Selected Node & Dynamic Replay Form
  const [selectedNode, setSelectedNode] = useState<GenericNode | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'state' | 'replay'>('state');
  const [dynamicInputs, setDynamicInputs] = useState<Record<string, any>>({});
  const [replaying, setReplaying] = useState(false);
  const [replayResult, setReplayResult] = useState<ReplayResponse | null>(null);
  const [replayError, setReplayError] = useState('');

  // Modal: Arbitrary Execution / Script Runner
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [entrypointCmd, setEntrypointCmd] = useState('python3 script.py');
  const [scriptCode, setScriptCode] = useState(`# Universal Python Tracer Test
import blackbox

@blackbox.trace
def process_data(item: str, count: int = 1):
    return {"item": item.upper(), "total": count * 10}

@blackbox.trace(name="calculate_score")
def evaluate(data: dict):
    return f"Processed {data['item']} with total {data['total']}"

tid = blackbox.new_trace()
res1 = process_data("sample_payload", 4)
res2 = evaluate(res1)
print("Finished execution:", res2)
`);
  const [executing, setExecuting] = useState(false);
  const [execOutput, setExecOutput] = useState<any>(null);

  // Check Backend
  const checkHealth = useCallback(() => {
    api.getStatus()
      .then(() => setBackendStatus('online'))
      .catch(() => setBackendStatus('offline'));
  }, []);

  // Fetch Trace List
  const fetchTraces = useCallback(async (autoSelectTraceId?: string) => {
    setLoadingTraces(true);
    try {
      const res = await api.listTraces();
      const list = res.traces || [];
      setTraces(list);
      if (autoSelectTraceId) {
        setSelectedTraceId(autoSelectTraceId);
      } else if (!selectedTraceId && list.length > 0) {
        setSelectedTraceId(list[0].trace_id);
      }
      return list;
    } catch {
      // Fail-safe
      return [];
    } finally {
      setLoadingTraces(false);
    }
  }, [selectedTraceId]);

  useEffect(() => {
    checkHealth();
    fetchTraces();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [checkHealth, fetchTraces]);

  // Load Trace DAG
  useEffect(() => {
    if (!selectedTraceId) {
      setActiveDag(null);
      setSelectedNode(null);
      setActiveDiagnosis(null);
      return;
    }

    setLoadingDag(true);
    setReplayResult(null);
    setReplayError('');

    Promise.all([
      api.getTrace(selectedTraceId).catch(() => null),
      api.diagnose(selectedTraceId).catch(() => null),
    ])
      .then(([dagRes, diagRes]) => {
        if (dagRes) {
          const nodes = dagRes.nodes || dagRes.steps || [];
          setActiveDag({ trace_id: dagRes.trace_id, nodes });
          const failedNode = nodes.find((n) => n.status === 'failed');
          const initialNode = failedNode || nodes[0] || null;
          setSelectedNode(initialNode);
          if (initialNode) {
            setDynamicInputs(initialNode.inputs || {});
          }
        }
        if (diagRes) {
          setActiveDiagnosis({
            status: diagRes.diagnosis.status,
            failure_type: diagRes.diagnosis.failure_type,
            root_cause: diagRes.diagnosis.root_cause,
            evidence: diagRes.diagnosis.evidence,
            explanation: diagRes.explanation,
          });
        } else {
          setActiveDiagnosis(null);
        }
      })
      .finally(() => setLoadingDag(false));
  }, [selectedTraceId]);

  const handleSelectNode = (node: GenericNode) => {
    setSelectedNode(node);
    setDynamicInputs(node.inputs || {});
    setReplayResult(null);
    setReplayError('');
  };

  // Trigger Universal Time-Travel Replay
  const handleExecuteReplay = async () => {
    if (!selectedTraceId || !selectedNode) return;
    setReplaying(true);
    setReplayError('');
    setReplayResult(null);

    try {
      const res = await api.replay(
        selectedTraceId,
        selectedNode.span_id || (selectedNode as any).step_id,
        dynamicInputs,
        undefined,
        entrypointCmd ? entrypointCmd.trim().split(/\s+/) : undefined
      );
      setReplayResult(res);
      await fetchTraces();
    } catch (e: any) {
      setReplayError(e?.message || String(e));
    } finally {
      setReplaying(false);
    }
  };

  // Run Arbitrary Code with Auto-Refresh & Auto-Select
  const handleRunArbitrary = async () => {
    setExecuting(true);
    setExecOutput(null);
    try {
      const res = await api.runExecution(
        undefined,
        scriptCode,
        undefined
      );
      setExecOutput(res);
      if (res.trace_id) {
        await fetchTraces(res.trace_id);
      } else {
        await fetchTraces();
      }
    } catch (e: any) {
      setExecOutput({ error: e?.message || String(e) });
    } finally {
      setExecuting(false);
    }
  };

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      const matchesStatus =
        statusFilter === 'all' ? true : statusFilter === 'failed' ? t.status === 'failed' : t.status === 'success';
      const matchesSearch =
        !searchQuery || t.trace_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [traces, statusFilter, searchQuery]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      
      {/* ──────────────────────────────────────────────────────────────────────────
          1. GLOBAL HEADER (60PX)
         ────────────────────────────────────────────────────────────────────────── */}
      <header
        style={{
          height: 60,
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-pane)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 6,
                background: 'linear-gradient(135deg, #10b981 0%, #3b82f6 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 700,
              }}
            >
              <Activity size={18} />
            </div>
            <div>
              <span style={{ fontWeight: 700, fontSize: 14 }}>BLACK BOX</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 6, padding: '1px 5px', border: '1px solid var(--border)', borderRadius: 4 }}>
                UNIVERSAL DEBUGGER
              </span>
            </div>
          </div>

          <div style={{ height: 20, width: 1, background: 'var(--border)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Layers size={14} color="var(--text-muted)" />
            <select
              value={project}
              onChange={(e) => setProject(e.target.value)}
              style={{ padding: '4px 8px', fontSize: 12, border: 'none', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}
            >
              <option value="Universal Execution Traces">Universal Execution Traces</option>
              <option value="LangChain / CrewAI Agents">LangChain / CrewAI Agents</option>
              <option value="Arbitrary Python Scripts">Arbitrary Python Scripts</option>
            </select>
          </div>
        </div>

        {/* Global Search */}
        <div style={{ display: 'flex', alignItems: 'center', width: 340, position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, color: 'var(--text-muted)' }} />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by Trace ID or Span ID..."
            style={{ width: '100%', padding: '6px 12px 6px 32px', fontSize: 12, borderRadius: 6, background: 'var(--bg-app)' }}
          />
        </div>

        {/* Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 11,
              padding: '4px 10px',
              borderRadius: 12,
              background: backendStatus === 'online' ? 'var(--green-glow)' : 'var(--red-bg)',
              color: backendStatus === 'online' ? 'var(--green)' : 'var(--red)',
              fontWeight: 600,
            }}
          >
            <Server size={12} />
            <span>{backendStatus === 'online' ? 'LIVE' : 'OFFLINE'}</span>
          </div>

          <button
            onClick={() => setIsRunModalOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              borderRadius: 6,
              background: 'var(--blue)',
              color: '#fff',
              border: 'none',
              fontWeight: 600,
              fontSize: 12,
            }}
          >
            <Play size={12} fill="#fff" />
            <span>Run Target Code</span>
          </button>

          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              background: 'var(--bg-active)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
            }}
          >
            <User size={16} />
          </div>
        </div>
      </header>

      {/* ──────────────────────────────────────────────────────────────────────────
          THREE-PANE WORKSPACE
         ────────────────────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* PANE A: TRACE HISTORY (~20%) */}
        <aside
          style={{
            width: '22%',
            minWidth: 260,
            maxWidth: 340,
            borderRight: '1px solid var(--border)',
            background: 'var(--bg-pane)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: 13 }}>
                <Clock size={14} color="var(--text-muted)" />
                <span>Recorded Traces</span>
                <span style={{ fontSize: 10, background: 'var(--bg-card)', padding: '2px 6px', borderRadius: 10, color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                  {filteredTraces.length}
                </span>
              </div>
              <button onClick={() => fetchTraces()} disabled={loadingTraces} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <RefreshCw size={13} className={loadingTraces ? 'animate-spin' : ''} />
              </button>
            </div>

            <select
              value={statusFilter}
              onChange={(e: any) => setStatusFilter(e.target.value)}
              style={{ width: '100%', padding: '6px 8px', fontSize: 11, background: 'var(--bg-app)' }}
            >
              <option value="all">Filter: All Traces</option>
              <option value="failed">Filter: Failed Traces Only</option>
              <option value="success">Filter: Successful Traces Only</option>
            </select>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {filteredTraces.map((t) => {
              const isSelected = t.trace_id === selectedTraceId;
              const isFailed = t.status === 'failed' || t.failed_steps > 0;

              return (
                <div
                  key={t.trace_id}
                  onClick={() => setSelectedTraceId(t.trace_id)}
                  style={{
                    background: isSelected ? 'var(--bg-active)' : 'var(--bg-card)',
                    border: `1px solid ${isSelected ? 'var(--blue)' : 'var(--border)'}`,
                    borderRadius: 6,
                    padding: '10px 12px',
                    cursor: 'pointer',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: 3,
                      borderTopLeftRadius: 6,
                      borderBottomLeftRadius: 6,
                      background: isFailed ? 'var(--red)' : 'var(--green)',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {isFailed ? <XCircle size={14} color="var(--red)" /> : <CheckCircle2 size={14} color="var(--green)" />}
                      <span style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace' }}>
                        {t.trace_id}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{formatTimeAgo(t.timestamp)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
                    <span>{t.total_steps} spans</span>
                    {isFailed && <span style={{ color: 'var(--red)', fontWeight: 500 }}>{t.failed_steps} failed</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </aside>

        {/* PANE B: GENERIC DAG CANVAS (~50%) */}
        <main style={{ flex: 1, background: 'var(--bg-app)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {loadingDag ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: 8 }}>
              <RefreshCw size={18} className="animate-spin" />
              <span>Loading execution DAG...</span>
            </div>
          ) : !activeDag ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', gap: 10 }}>
              <Database size={32} color="var(--text-dim)" />
              <p>Select a trace to view its dynamic DAG graph.</p>
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
              
              {/* AI Diagnostic Alert Banner */}
              {activeDiagnosis && activeDiagnosis.status === 'failure_detected' && (
                <div style={{ padding: '16px 20px 0' }}>
                  <div
                    style={{
                      background: 'linear-gradient(90deg, rgba(244, 63, 94, 0.15) 0%, rgba(244, 63, 94, 0.05) 100%)',
                      border: '1px solid var(--red)',
                      borderRadius: 8,
                      padding: '14px 18px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: 16,
                    }}
                  >
                    <div style={{ display: 'flex', gap: 12 }}>
                      <AlertTriangle size={20} color="var(--red)" />
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <strong style={{ color: 'var(--red)', fontSize: 13 }}>DIAGNOSED ROOT CAUSE</strong>
                          {activeDiagnosis.failure_type && (
                            <span style={{ fontSize: 10, background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid var(--red)', padding: '1px 6px', borderRadius: 4 }}>
                              {activeDiagnosis.failure_type}
                            </span>
                          )}
                        </div>
                        <p style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.5 }}>
                          {activeDiagnosis.explanation || activeDiagnosis.root_cause?.error}
                        </p>
                      </div>
                    </div>

                    {activeDiagnosis.root_cause?.step_id && (
                      <button
                        onClick={() => {
                          const n = activeDag.nodes.find(
                            (x) => x.span_id === activeDiagnosis.root_cause?.step_id || (x as any).step_id === activeDiagnosis.root_cause?.step_id
                          );
                          if (n) handleSelectNode(n);
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '6px 12px',
                          background: 'var(--red)',
                          color: '#fff',
                          border: 'none',
                          borderRadius: 6,
                          fontWeight: 600,
                          fontSize: 11,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        <Zap size={13} />
                        <span>Jump to Fault Node</span>
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Dynamic DAG Topology View */}
              <div style={{ padding: '20px', flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div>
                    <h2 style={{ fontSize: 15, fontWeight: 700 }}>Execution Graph (DAG)</h2>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Generic function span hierarchy dynamically captured across execution.
                    </p>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    Trace: {activeDag.trace_id}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 0, paddingLeft: 10 }}>
                  {activeDag.nodes.map((node, idx) => {
                    const isSelected = selectedNode?.span_id === node.span_id;
                    const isRootCause =
                      node.status === 'failed' ||
                      node.span_id === activeDiagnosis?.root_cause?.step_id ||
                      (node as any).step_id === activeDiagnosis?.root_cause?.step_id;
                    const isChild = Boolean(node.parent_span_id);

                    return (
                      <div key={node.span_id || idx} style={{ display: 'flex', flexDirection: 'column', marginLeft: isChild ? 24 : 0 }}>
                        <div
                          onClick={() => handleSelectNode(node)}
                          className={isRootCause ? 'root-cause-pulse' : ''}
                          style={{
                            background: isSelected
                              ? 'var(--bg-active)'
                              : isRootCause
                              ? 'rgba(244, 63, 94, 0.08)'
                              : 'var(--bg-card)',
                            border: `1px solid ${
                              isRootCause ? 'var(--red)' : isSelected ? 'var(--blue)' : 'var(--border)'
                            }`,
                            borderRadius: 8,
                            padding: '12px 16px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            zIndex: 2,
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            {isChild && <GitBranch size={14} color="var(--text-muted)" />}
                            <div
                              style={{
                                width: 26,
                                height: 26,
                                borderRadius: '50%',
                                background: isRootCause ? 'var(--red)' : node.status === 'success' ? 'var(--green)' : 'var(--bg-app)',
                                color: '#fff',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: 700,
                                fontSize: 11,
                              }}
                            >
                              {idx + 1}
                            </div>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <strong style={{ fontSize: 13 }}>{node.function_name || (node as any).name}</strong>
                                {isRootCause && (
                                  <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 3, background: 'var(--red)', color: '#fff', fontWeight: 600 }}>
                                    ROOT CAUSE
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                                span_id: {node.span_id} · {node.duration_ms != null ? `${node.duration_ms.toFixed(1)}ms` : '0ms'}
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectNode(node);
                                setInspectorTab('replay');
                              }}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 4,
                                padding: '4px 8px',
                                borderRadius: 4,
                                background: 'transparent',
                                border: '1px solid var(--border-active)',
                                color: 'var(--text-muted)',
                                fontSize: 11,
                              }}
                            >
                              <RotateCcw size={11} />
                              <span>Replay</span>
                            </button>
                            <ChevronRight size={16} color="var(--text-muted)" />
                          </div>
                        </div>

                        {idx < activeDag.nodes.length - 1 && (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: 24, width: 26, marginLeft: 13 }}>
                            <div style={{ width: 2, height: '100%', background: 'var(--border-active)' }} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </main>

        {/* PANE C: DYNAMIC NODE INSPECTOR & TIME-TRAVEL REPLAY (~30%) */}
        <aside
          style={{
            width: '32%',
            minWidth: 360,
            maxWidth: 480,
            borderLeft: '1px solid var(--border)',
            background: 'var(--bg-pane)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
              
              <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700 }}>{selectedNode.function_name || (selectedNode as any).name}</h3>
                  <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: selectedNode.status === 'success' ? 'var(--green-glow)' : 'var(--red-bg)', color: selectedNode.status === 'success' ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                    {selectedNode.status.toUpperCase()}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: 4, background: 'var(--bg-app)', padding: 3, borderRadius: 6, border: '1px solid var(--border)' }}>
                  <button
                    onClick={() => setInspectorTab('state')}
                    style={{
                      flex: 1,
                      padding: '5px 10px',
                      fontSize: 11,
                      fontWeight: 600,
                      borderRadius: 4,
                      border: 'none',
                      background: inspectorTab === 'state' ? 'var(--bg-card)' : 'transparent',
                      color: inspectorTab === 'state' ? 'var(--text)' : 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                    }}
                  >
                    <Eye size={12} />
                    <span>View State</span>
                  </button>
                  <button
                    onClick={() => setInspectorTab('replay')}
                    style={{
                      flex: 1,
                      padding: '5px 10px',
                      fontSize: 11,
                      fontWeight: 600,
                      borderRadius: 4,
                      border: 'none',
                      background: inspectorTab === 'replay' ? 'var(--blue)' : 'transparent',
                      color: inspectorTab === 'replay' ? '#fff' : 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                    }}
                  >
                    <RotateCcw size={12} />
                    <span>Edit & Replay</span>
                  </button>
                </div>
              </div>

              <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                {inspectorTab === 'state' ? (
                  <>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6, fontWeight: 600 }}>
                        Inputs Payload
                      </div>
                      <pre style={{ background: 'var(--bg-app)', border: '1px solid var(--border)', borderRadius: 6, padding: '10px 12px', fontSize: 11, fontFamily: 'monospace', color: 'var(--text)' }}>
                        {JSON.stringify(selectedNode.inputs || {}, null, 2)}
                      </pre>
                    </div>

                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6, fontWeight: 600 }}>
                        Outputs / Return Value
                      </div>
                      <pre style={{ background: 'var(--bg-app)', border: '1px solid var(--border)', borderRadius: 6, padding: '10px 12px', fontSize: 11, fontFamily: 'monospace', color: selectedNode.status === 'failed' ? 'var(--red)' : 'var(--text)' }}>
                        {JSON.stringify(selectedNode.outputs || {}, null, 2)}
                      </pre>
                    </div>

                    {selectedNode.error && (
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--red)', textTransform: 'uppercase', marginBottom: 6, fontWeight: 600 }}>
                          Runtime Exception
                        </div>
                        <pre style={{ background: 'var(--red-bg)', border: '1px solid var(--red)', borderRadius: 6, padding: '10px 12px', fontSize: 11, color: 'var(--red)', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                          {selectedNode.error}
                        </pre>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div style={{ background: 'var(--bg-app)', border: '1px solid var(--border)', borderRadius: 6, padding: '10px 12px', fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                      <strong style={{ color: 'var(--blue)' }}>Generic Time-Travel Active:</strong> Dynamically editing input parameters for span <code>{selectedNode.span_id}</code>. Unaffected upstream spans remain stubbed from cache.
                    </div>

                    {/* DYNAMIC FORM GENERATION FROM EXACT KEYS IN INPUTS_JSON */}
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8, fontWeight: 600 }}>
                        Dynamically Generated Parameters
                      </div>
                      <DynamicInputForm
                        inputs={dynamicInputs}
                        onChange={(updated) => setDynamicInputs(updated)}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600 }}>
                        ENTRYPOINT COMMAND / SCRIPT (OPTIONAL)
                      </label>
                      <input
                        value={entrypointCmd}
                        onChange={(e) => setEntrypointCmd(e.target.value)}
                        placeholder="e.g. python3 main.py"
                        style={{ width: '100%', padding: '6px 10px', fontSize: 11, fontFamily: 'monospace' }}
                      />
                    </div>

                    <button
                      onClick={handleExecuteReplay}
                      disabled={replaying}
                      style={{
                        padding: '10px 16px',
                        background: 'var(--blue)',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        fontWeight: 600,
                        fontSize: 12,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 8,
                      }}
                    >
                      {replaying ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
                      <span>{replaying ? 'Executing Replay...' : 'Execute Time-Travel Replay'}</span>
                    </button>

                    {replayError && <p style={{ color: 'var(--red)', fontSize: 12 }}>{replayError}</p>}

                    {/* Replay Diff Comparison */}
                    {replayResult && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4, background: 'var(--green-glow)', color: 'var(--green)' }}>
                            STATUS: {replayResult.comparison.status.toUpperCase()}
                          </span>
                        </div>

                        {replayResult.comparison.checkpoint && (
                          <div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6, fontWeight: 600 }}>
                              Checkpoint Comparison Diff
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                              <div>
                                <span style={{ fontSize: 10, color: 'var(--red)' }}>- Original State:</span>
                                <pre style={{ background: 'var(--bg-app)', border: '1px solid var(--border)', borderRadius: 4, padding: '6px 8px', fontSize: 10, fontFamily: 'monospace' }}>
                                  {JSON.stringify(replayResult.comparison.checkpoint.original_output, null, 2)}
                                </pre>
                              </div>
                              <div>
                                <span style={{ fontSize: 10, color: 'var(--green)' }}>+ Modified State:</span>
                                <pre style={{ background: 'var(--bg-app)', border: '1px solid var(--green)', borderRadius: 4, padding: '6px 8px', fontSize: 10, fontFamily: 'monospace' }}>
                                  {JSON.stringify(replayResult.comparison.checkpoint.modified_output, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', padding: 24, textAlign: 'center', gap: 8 }}>
              <CornerDownRight size={24} color="var(--text-dim)" />
              <p style={{ fontSize: 13 }}>Click on any node in the execution DAG to inspect state or perform time-travel replay.</p>
            </div>
          )}
        </aside>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────────
          MODAL: ARBITRARY SCRIPT / ENTRYPOINT RUNNER
         ────────────────────────────────────────────────────────────────────────── */}
      {isRunModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              width: '90%',
              maxWidth: 620,
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Terminal size={18} color="var(--blue)" />
                <h3 style={{ fontSize: 16, fontWeight: 700 }}>Execute Target Code</h3>
              </div>
              <button
                onClick={() => setIsRunModalOpen(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}
              >
                ✕
              </button>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                PYTHON CODE WITH @blackbox.trace DECORATORS
              </label>
              <textarea
                value={scriptCode}
                onChange={(e) => setScriptCode(e.target.value)}
                rows={10}
                style={{ width: '100%', padding: '10px 12px', resize: 'vertical', fontFamily: 'monospace', fontSize: 11 }}
              />
            </div>

            {execOutput && (
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>EXECUTION OUTPUT</div>
                <pre style={{ background: 'var(--bg-app)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 10px', fontSize: 11, fontFamily: 'monospace' }}>
                  {execOutput.stdout || execOutput.stderr || JSON.stringify(execOutput, null, 2)}
                </pre>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                onClick={() => setIsRunModalOpen(false)}
                style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-muted)' }}
              >
                Close
              </button>
              <button
                onClick={handleRunArbitrary}
                disabled={executing}
                style={{
                  padding: '8px 18px',
                  background: 'var(--blue)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {executing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} fill="#fff" />}
                <span>{executing ? 'Executing...' : 'Run & Trace'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
