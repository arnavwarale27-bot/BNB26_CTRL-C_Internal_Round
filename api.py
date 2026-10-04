from typing import Any, List, Optional
import os
import tempfile

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from blackbox.database import TraceDatabase
from blackbox.unified_diagnosis import UnifiedDiagnosis
from blackbox.explanation import FailureExplanation
from blackbox.coding_recorder import CodingRecorder
from blackbox.execution_result import ExecutionResult


app = FastAPI(
    title="Black Box",
    description="Flight Recorder and Execution Debugger for AI Coding Agents",
    version="1.0.0"
)


# ============================================================
# REQUEST MODELS
# ============================================================

class DiagnoseRequest(BaseModel):
    trace_id: str
    expected_path: List[str]
    expected_output: Optional[Any] = None


class CodingExecutionRequest(BaseModel):
    command: List[str]
    cwd: Optional[str] = None


class CodeExecutionRequest(BaseModel):
    code: str
    filename: str = "agent_code.py"


class AgentExecutionRequest(BaseModel):
    task: str
    commands: List[List[str]]
    expected_path: Optional[List[str]] = None
    expected_output: Optional[Any] = None
    cwd: Optional[str] = None


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "name": "Black Box",
        "description": "Flight Recorder for AI Coding Agents",
        "status": "running"
    }


# ============================================================
# GET TRACE
# ============================================================

@app.get("/traces/{trace_id}")
def get_trace(trace_id: str):

    db = TraceDatabase()

    trace = db.get_trace(trace_id)

    if not trace:

        raise HTTPException(
            status_code=404,
            detail="Trace not found"
        )

    return {
        "trace_id": trace_id,
        "steps": trace
    }


# ============================================================
# CODING EXECUTION
# ============================================================

@app.post("/coding/execute")
def coding_execute(request: CodingExecutionRequest):

    recorder = CodingRecorder()

    try:

        recorder.run_command(
            command=request.command,
            cwd=request.cwd
        )

    except Exception:

        pass

    trace = recorder.get_trace()

    result = ExecutionResult().build(trace)

    return {
        "trace_id": recorder.recorder.trace_id,
        "result": result
    }


# ============================================================
# RUN PYTHON CODE
# ============================================================

@app.post("/coding/run-code")
def run_code(request: CodeExecutionRequest):

    temp_dir = tempfile.mkdtemp()

    filename = os.path.basename(
        request.filename
    )

    if not filename.endswith(".py"):

        filename = filename + ".py"

    file_path = os.path.join(
        temp_dir,
        filename
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(request.code)

    recorder = CodingRecorder()

    try:

        recorder.run_command(
            command=[
                "python",
                file_path
            ],
            cwd=temp_dir
        )

    except Exception:

        pass

    trace = recorder.get_trace()

    result = ExecutionResult().build(trace)

    return {
        "trace_id": recorder.recorder.trace_id,
        "filename": filename,
        "result": result
    }


# ============================================================
# DIAGNOSE EXISTING TRACE
# ============================================================

@app.post("/diagnose")
def diagnose(request: DiagnoseRequest):

    db = TraceDatabase()

    trace = db.get_trace(
        request.trace_id
    )

    if not trace:

        raise HTTPException(
            status_code=404,
            detail="Trace not found"
        )

    diagnosis = UnifiedDiagnosis().diagnose(
        trace=trace,
        expected_path=request.expected_path,
        expected_output=request.expected_output
    )

    explanation = FailureExplanation().explain(
        diagnosis
    )

    return {
        "trace_id": request.trace_id,
        "diagnosis": diagnosis,
        "explanation": explanation
    }


# ============================================================
# MULTI-STEP AI AGENT EXECUTION
# ============================================================

@app.post("/agent/execute")
def agent_execute(
    request: AgentExecutionRequest
):

    recorder = CodingRecorder()

    # Execute every step of the agent workflow
    for command in request.commands:

        try:

            recorder.run_command(
                command=command,
                cwd=request.cwd
            )

        except Exception:

            # Continue recording the workflow
            # even if one step fails.
            continue

    # Get complete execution trace
    trace = recorder.get_trace()

    # Build clean execution result
    result = ExecutionResult().build(
        trace
    )

    response = {
        "trace_id": recorder.recorder.trace_id,
        "task": request.task,
        "result": result
    }

    # Run diagnosis when expected path is provided
    if request.expected_path is not None:

        diagnosis = UnifiedDiagnosis().diagnose(
            trace=trace,
            expected_path=request.expected_path,
            expected_output=request.expected_output
        )

        explanation = FailureExplanation().explain(
            diagnosis
        )

        response["diagnosis"] = diagnosis

        response["explanation"] = explanation

    return response


# ============================================================
# FRONTEND-FRIENDLY AGENT HISTORY
# ============================================================

@app.get("/agent/history/{trace_id}")
def agent_history(
    trace_id: str
):

    db = TraceDatabase()

    trace = db.get_trace(
        trace_id
    )

    if not trace:

        raise HTTPException(
            status_code=404,
            detail="Trace not found"
        )

    result = ExecutionResult().build(
        trace
    )

    failed_steps = [
        {
            "step_id": event.get(
                "step_id"
            ),

            "name": event.get(
                "name"
            ),

            "error": event.get(
                "error"
            ),

            "status": event.get(
                "status"
            )
        }

        for event in trace

        if event.get(
            "status"
        ) == "failed"
    ]

    return {
        "trace_id": trace_id,

        "status": result[
            "status"
        ],

        "total_steps": len(
            trace
        ),

        "history": result[
            "history"
        ],

        "failed_steps": failed_steps
    }
