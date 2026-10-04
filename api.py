from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import subprocess
import sys
import tempfile
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from blackbox.config import settings
from blackbox.database import GenericTraceDatabase
from blackbox.models import GenericSpan, IngestSpansRequest, GenericReplayRequest
from blackbox.replay import ReplayEngine
from blackbox.comparator import TraceComparator
from blackbox.llm_diagnosis import LLMDiagnosisEngine


app = FastAPI(
    title="Black Box",
    description="Universal, Framework-Agnostic AI Debugger & Flight Recorder",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GENERIC REQUEST MODELS
# ============================================================

class GenericDiagnoseRequest(BaseModel):
    trace_id: str
    expected_path: Optional[List[str]] = None
    expected_output: Optional[Any] = None

    class Config:
        extra = "allow"


class ArbitraryRunRequest(BaseModel):
    entrypoint_command: Optional[List[str]] = None
    code: Optional[str] = None
    cwd: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None


# ============================================================
# ROOT HEALTH PROBE
# ============================================================

@app.get("/")
def root():
    return {
        "platform": "Black Box",
        "description": "Universal Framework-Agnostic Observability & Replay Platform",
        "version": "2.1.0",
        "status": "running"
    }


# ============================================================
# GENERIC GRAPH & SPAN INGESTION (REAL DATABASE INSERTION)
# ============================================================

@app.post("/traces")
@app.post("/traces/ingest")
async def ingest_spans(request: Request):
    """
    Receives JSON trace payload (single span, array of spans, or object with spans/events)
    and executes a real INSERT statement into the SQLite database.
    Returns 200 OK with the trace_id.
    """
    body = await request.json()

    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        if "spans" in body:
            items = body["spans"]
        elif "events" in body:
            items = body["events"]
        else:
            # Single span payload: { "trace_id": ..., "name": ..., "inputs": ..., "outputs": ..., "status": ... }
            items = [body]
    else:
        items = []

    spans_to_save: List[GenericSpan] = []
    primary_trace_id = "run_default"

    for item in items:
        tid = item.get("trace_id") or primary_trace_id
        primary_trace_id = tid

        # Handle outputs
        outputs = item.get("outputs")
        if outputs is None:
            if "result" in item:
                outputs = {"result": item.get("result")}
            else:
                outputs = {}

        spans_to_save.append(
            GenericSpan(
                trace_id=tid,
                span_id=item.get("span_id") or item.get("step_id") or f"span_{uuid.uuid4().hex[:8]}",
                parent_span_id=item.get("parent_span_id") or item.get("parent_step_id"),
                function_name=item.get("function_name") or item.get("name") or "anonymous_step",
                inputs=item.get("inputs") or {},
                outputs=outputs,
                locals=item.get("locals") or {},
                timestamp=item.get("timestamp") or datetime.now(timezone.utc),
                duration_ms=item.get("duration_ms"),
                status=item.get("status") or "success",
                error=item.get("error"),
                metadata=item.get("metadata") or {}
            )
        )

    db = GenericTraceDatabase()
    db.save_spans(spans_to_save)

    return {
        "status": "success",
        "trace_id": primary_trace_id,
        "ingested_count": len(spans_to_save)
    }


# ============================================================
# GENERIC DAG QUERIES
# ============================================================

@app.get("/traces")
def list_traces():
    """
    Returns high-level DAG trace summaries recorded in SQLite.
    """
    db = GenericTraceDatabase()
    return {
        "traces": db.list_traces()
    }


@app.get("/traces/{trace_id}")
def get_trace_dag(trace_id: str):
    """
    Retrieves the complete generic DAG of nodes and edges for any trace.
    """
    db = GenericTraceDatabase()
    spans = db.get_trace(trace_id)

    if not spans:
        raise HTTPException(
            status_code=404,
            detail=f"Trace DAG '{trace_id}' not found in database."
        )

    return {
        "trace_id": trace_id,
        "nodes": spans,
        "steps": spans  # Backward-compatible alias
    }


# ============================================================
# UNIVERSAL REPLAY ENGINE
# ============================================================

@app.post("/replay")
async def replay_execution(request: Request):
    """
    Universal Time-Travel Replay:
    - Stubs spans 1..N-1 from SQLite cache.
    - Injects modified inputs/outputs at span N.
    - Executes live from span N forward via dynamic Python dispatch or subprocess.
    """
    body = await request.json()
    trace_id = body.get("trace_id")
    checkpoint_span_id = body.get("checkpoint_span_id") or body.get("checkpoint_step_id")
    modified_output = body.get("modified_output")
    modified_inputs = body.get("modified_inputs")

    if not trace_id or not checkpoint_span_id:
        raise HTTPException(
            status_code=400,
            detail="trace_id and checkpoint_span_id are required."
        )

    db = GenericTraceDatabase()
    original_dag = db.get_trace(trace_id)

    if not original_dag:
        raise HTTPException(
            status_code=404,
            detail=f"Trace DAG '{trace_id}' not found."
        )

    engine = ReplayEngine()
    try:
        replay_dag = engine.replay(
            trace=original_dag,
            checkpoint_step_id=checkpoint_span_id,
            modified_output=modified_output or modified_inputs
        )
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    comparison = TraceComparator().compare(
        original_trace=original_dag,
        replay_trace=replay_dag
    )

    return {
        "trace_id": trace_id,
        "checkpoint_span_id": checkpoint_span_id,
        "replay_dag": replay_dag,
        "replay_trace": replay_dag,
        "comparison": comparison
    }


# ============================================================
# UNIVERSAL AI DIAGNOSIS
# ============================================================

@app.post("/diagnose")
def diagnose_generic_trace(request: GenericDiagnoseRequest):
    """
    Runs LLM-as-a-judge failure analysis across arbitrary code execution DAGs.
    """
    db = GenericTraceDatabase()
    spans = db.get_trace(request.trace_id)

    if not spans:
        raise HTTPException(
            status_code=404,
            detail=f"Trace '{request.trace_id}' not found."
        )

    diagnosis_engine = LLMDiagnosisEngine()
    diagnosis = diagnosis_engine.diagnose(
        trace=spans,
        expected_path=request.expected_path,
        expected_output=request.expected_output
    )

    return {
        "trace_id": request.trace_id,
        "diagnosis": diagnosis,
        "explanation": diagnosis.get("explanation", "")
    }


# ============================================================
# ARBITRARY SCRIPT / ENTRYPOINT RUNNER (DYNAMIC TELEMETRY INJECTION)
# ============================================================

@app.post("/execution/run")
def run_arbitrary_code(request: ArbitraryRunRequest):
    """
    Executes any arbitrary Python script or entrypoint command.
    Dynamically injects the self-contained BlackBox tracing logic and PYTHONPATH
    so executing in temporary directories never throws ModuleNotFoundError and
    always posts traces directly to the /traces database endpoint.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    trace_id = f"run_{uuid.uuid4().hex[:8]}"

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{existing_pythonpath}" if existing_pythonpath else project_root
    env["BLACKBOX_API_URL"] = settings.api_url
    env["BLACKBOX_TRACE_ID"] = trace_id

    if request.env_vars:
        env.update(request.env_vars)

    if request.code:
        # Prepend universal Black Box telemetry injector directly into script code
        injected_bootstrap = f"""# --- INJECTED BLACKBOX TELEMETRY MODULE ---
import sys, os, json, time, uuid, urllib.request, functools, inspect
from datetime import datetime, timezone

_PROJECT_ROOT = {repr(project_root)}
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_TRACE_ID = os.getenv("BLACKBOX_TRACE_ID", {repr(trace_id)})
_API_URL = os.getenv("BLACKBOX_API_URL", {repr(settings.api_url)})

class _InjectedBlackBoxSDK:
    def __init__(self, api_url=_API_URL, trace_id=_TRACE_ID):
        self.api_url = api_url.rstrip("/")
        self.trace_id = trace_id
        self._current_parent = None

    def new_trace(self, tid=None):
        if tid:
            self.trace_id = tid
        return self.trace_id

    def get_current_trace_id(self):
        return self.trace_id

    def emit_span(self, span_dict):
        try:
            url = f"{{self.api_url}}/traces"
            data = json.dumps(span_dict).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={{"Content-Type": "application/json"}},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                pass
        except Exception:
            pass

    def trace(self, func_or_name=None, **kwargs):
        def dec(fn):
            fn_name = (func_or_name if isinstance(func_or_name, str) else kwargs.get("name")) or fn.__name__
            sig = inspect.signature(fn)

            @functools.wraps(fn)
            def wrapper(*args, **kw):
                span_id = f"span_{{uuid.uuid4().hex[:8]}}"
                parent_id = self._current_parent
                self._current_parent = span_id

                inputs = {{}}
                try:
                    bound = sig.bind(*args, **kw)
                    bound.apply_defaults()
                    for k, v in bound.arguments.items():
                        try:
                            json.dumps(v)
                            inputs[k] = v
                        except:
                            inputs[k] = str(v)
                except Exception:
                    inputs = {{"args": [str(a) for a in args], "kwargs": {{str(k): str(v) for k, v in kw.items()}}}}

                start = time.perf_counter()
                status = "success"
                error = None
                out = None
                try:
                    out = fn(*args, **kw)
                    return out
                except Exception as ex:
                    status = "failed"
                    error = f"{{type(ex).__name__}}: {{str(ex)}}"
                    raise ex
                finally:
                    dur = round((time.perf_counter() - start) * 1000, 2)
                    try:
                        json.dumps(out)
                        safe_out = {{"result": out}}
                    except:
                        safe_out = {{"result": str(out)}}

                    span = {{
                        "trace_id": self.trace_id,
                        "span_id": span_id,
                        "parent_span_id": parent_id,
                        "name": fn_name,
                        "function_name": fn_name,
                        "inputs": inputs,
                        "outputs": safe_out,
                        "duration_ms": dur,
                        "status": status,
                        "error": error,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }}
                    self.emit_span(span)
                    self._current_parent = parent_id

            return wrapper

        if callable(func_or_name):
            return dec(func_or_name)
        return dec

blackbox = _InjectedBlackBoxSDK()
trace = blackbox.trace
new_trace = blackbox.new_trace
get_current_trace_id = blackbox.get_current_trace_id

# Make sure importing blackbox in user code uses this configured instance
sys.modules['blackbox'] = blackbox
# --- END INJECTED TELEMETRY ---

"""
        full_code = injected_bootstrap + request.code

        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "target_script.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_code)

        cmd = [sys.executable, file_path]
        cwd = temp_dir
    elif request.entrypoint_command:
        cmd = request.entrypoint_command
        cwd = request.cwd or project_root
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'code' or 'entrypoint_command'."
        )

    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True
    )

    return {
        "status": "success" if proc.returncode == 0 else "failed",
        "trace_id": trace_id,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "command": cmd
    }
