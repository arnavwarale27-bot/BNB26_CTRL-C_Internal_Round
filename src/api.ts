const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Generic DAG Node Types ───────────────────────────────────────────────────

export interface GenericNode {
  trace_id: string;
  span_id: string;
  step_id?: string;
  parent_span_id: string | null;
  parent_step_id?: string | null;
  function_name: string;
  name?: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  locals?: Record<string, any>;
  timestamp: string;
  duration_ms: number | null;
  status: 'success' | 'failed' | 'running';
  error: string | null;
  metadata: Record<string, any>;
}

export interface TraceDagResponse {
  trace_id: string;
  nodes: GenericNode[];
  steps?: GenericNode[];
}

export interface TraceListItem {
  trace_id: string;
  timestamp: string;
  total_steps: number;
  total_spans?: number;
  failed_steps: number;
  total_duration_ms?: number;
  status: string;
}

export interface ListTracesResponse {
  traces: TraceListItem[];
}

export interface ReplayResponse {
  trace_id: string;
  checkpoint_span_id: string;
  replay_dag: GenericNode[];
  replay_trace?: GenericNode[];
  comparison: {
    status: string;
    checkpoint: {
      step_id: string;
      name: string;
      original_output: unknown;
      modified_output: unknown;
    } | null;
    downstream_effects: Array<{
      step_id: string;
      name: string;
      type: string;
      original_output: unknown;
      replay_output: unknown;
    }>;
  };
}

export interface DiagnoseResponse {
  trace_id: string;
  diagnosis: {
    status: string;
    failure_type: string | null;
    root_cause: { step_id: string | null; name: string | null; error: string | null } | null;
    evidence: Record<string, unknown>;
  };
  explanation: string;
}

// ── API calls ────────────────────────────────────────────────────────────────

export const api = {
  getStatus: () => request<{ platform: string; status: string }>('/'),

  listTraces: () => request<ListTracesResponse>('/traces'),

  getTrace: (trace_id: string) => request<TraceDagResponse>(`/traces/${trace_id}`),

  replay: (
    trace_id: string,
    checkpoint_span_id: string,
    modified_inputs?: Record<string, any>,
    modified_output?: any,
    entrypoint_command?: string[]
  ) =>
    request<ReplayResponse>('/replay', {
      method: 'POST',
      body: JSON.stringify({
        trace_id,
        checkpoint_span_id,
        modified_inputs,
        modified_output,
        entrypoint_command,
      }),
    }),

  diagnose: (trace_id: string, expected_path?: string[], expected_output?: any) =>
    request<DiagnoseResponse>('/diagnose', {
      method: 'POST',
      body: JSON.stringify({ trace_id, expected_path, expected_output }),
    }),

  runExecution: (
    entrypoint_command?: string[],
    code?: string,
    cwd?: string,
    env_vars?: Record<string, string>
  ) =>
    request<{
      status: string;
      trace_id: string;
      exit_code: number;
      stdout: string;
      stderr: string;
      command: string[];
    }>('/execution/run', {
      method: 'POST',
      body: JSON.stringify({ entrypoint_command, code, cwd, env_vars }),
    }),
};
