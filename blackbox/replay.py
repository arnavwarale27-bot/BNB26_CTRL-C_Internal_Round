import copy
import subprocess
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from .database import TraceDatabase
from .models import TraceEvent
from .sdk import get_registered_function


class ReplayEngine:
    """
    Production Checkpoint Replay Engine.

    Executes real live re-execution from checkpoint forward:
    - Steps 1..N-1: Deterministic stubbing (loaded from SQLite database cache).
    - Step N: Injects user modifications.
    - Steps N+1..forward: Re-executes registered Python functions or shell commands live.
    - Persists the new replayed trace into SQLite.
    """

    def replay(
        self,
        trace: List[Dict[str, Any]],
        checkpoint_step_id: str,
        modified_output: Any,
        downstream_functions: Optional[Dict[str, Callable]] = None,
        persist: bool = True
    ) -> List[Dict[str, Any]]:

        if not trace:
            raise ValueError("Cannot replay an empty trace.")

        downstream_functions = downstream_functions or {}
        checkpoint_found = False
        replay_trace: List[Dict[str, Any]] = []
        new_replay_trace_id = f"replay_{trace[0].get('trace_id', 'run')}_{uuid.uuid4().hex[:6]}"
        current_data = modified_output

        for event in trace:
            step_id = event.get("step_id")
            name = event.get("name", "unnamed_step")

            # ── 1. Steps before checkpoint: Preserve cached output (Stubbing) ──
            if not checkpoint_found:
                if step_id == checkpoint_step_id:
                    checkpoint_found = True

                    replay_event = copy.deepcopy(event)
                    replay_event["trace_id"] = new_replay_trace_id
                    replay_event["outputs"] = {"result": modified_output}
                    replay_event["status"] = "success"
                    replay_event["error"] = None
                    replay_event["metadata"] = {
                        **event.get("metadata", {}),
                        "replayed": True,
                        "checkpoint": True,
                        "original_output": event.get("outputs", {}).get("result")
                    }
                    replay_trace.append(replay_event)
                else:
                    stub_event = copy.deepcopy(event)
                    stub_event["trace_id"] = new_replay_trace_id
                    stub_event["metadata"] = {
                        **stub_event.get("metadata", {}),
                        "replayed": False,
                        "cached_stub": True
                    }
                    replay_trace.append(stub_event)
                continue

            # ── 2. Steps after checkpoint: Live re-execution ──
            # Try to resolve callable from provided functions or global SDK registry
            func = downstream_functions.get(name) or get_registered_function(name)

            if func is not None:
                start_time = time.perf_counter()
                try:
                    # Execute the real Python function with current upstream data
                    if isinstance(current_data, dict):
                        try:
                            exec_result = func(**current_data)
                        except TypeError:
                            exec_result = func(current_data)
                    else:
                        exec_result = func(current_data)

                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    current_data = exec_result

                    replay_event = copy.deepcopy(event)
                    replay_event["trace_id"] = new_replay_trace_id
                    replay_event["outputs"] = {"result": exec_result}
                    replay_event["status"] = "success"
                    replay_event["duration_ms"] = round(duration_ms, 2)
                    replay_event["error"] = None
                    replay_event["metadata"] = {
                        **event.get("metadata", {}),
                        "replayed": True,
                        "checkpoint": False,
                        "execution_type": "python_callable"
                    }
                    replay_trace.append(replay_event)

                except Exception as ex:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    replay_event = copy.deepcopy(event)
                    replay_event["trace_id"] = new_replay_trace_id
                    replay_event["outputs"] = {"result": None}
                    replay_event["status"] = "failed"
                    replay_event["duration_ms"] = round(duration_ms, 2)
                    replay_event["error"] = f"{type(ex).__name__}: {str(ex)}"
                    replay_event["metadata"] = {
                        **event.get("metadata", {}),
                        "replayed": True,
                        "checkpoint": False
                    }
                    replay_trace.append(replay_event)
                    break

            # If it was a subprocess/command step, execute live via subprocess
            elif event.get("event_type") == "command_execution" or "command" in event.get("inputs", {}):
                cmd = event.get("inputs", {}).get("command")
                if isinstance(cmd, list):
                    start_time = time.perf_counter()
                    try:
                        proc = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        status = "success" if proc.returncode == 0 else "failed"

                        replay_event = copy.deepcopy(event)
                        replay_event["trace_id"] = new_replay_trace_id
                        replay_event["outputs"] = {
                            "stdout": proc.stdout,
                            "stderr": proc.stderr,
                            "exit_code": proc.returncode,
                            "result": proc.stdout.strip()
                        }
                        replay_event["status"] = status
                        replay_event["duration_ms"] = round(duration_ms, 2)
                        replay_event["error"] = proc.stderr.strip() if proc.returncode != 0 else None
                        replay_event["metadata"] = {
                            **event.get("metadata", {}),
                            "replayed": True,
                            "execution_type": "subprocess"
                        }
                        replay_trace.append(replay_event)
                        if status == "failed":
                            break
                    except Exception as err:
                        replay_event = copy.deepcopy(event)
                        replay_event["trace_id"] = new_replay_trace_id
                        replay_event["status"] = "failed"
                        replay_event["error"] = str(err)
                        replay_trace.append(replay_event)
                        break
            else:
                # Default downstream data propagation
                replay_event = copy.deepcopy(event)
                replay_event["trace_id"] = new_replay_trace_id
                replay_event["status"] = "success"
                replay_event["metadata"] = {
                    **event.get("metadata", {}),
                    "replayed": True,
                    "downstream_propagated": True
                }
                replay_trace.append(replay_event)

        if not checkpoint_found:
            raise ValueError(f"Checkpoint step '{checkpoint_step_id}' was not found in trace.")

        # Persist new replayed trace into SQLite database
        if persist and replay_trace:
            db = TraceDatabase()
            events_to_save = [
                TraceEvent(
                    trace_id=ev.get("trace_id", new_replay_trace_id),
                    step_id=ev.get("step_id", f"step_{uuid.uuid4().hex[:8]}"),
                    parent_step_id=ev.get("parent_step_id"),
                    event_type=ev.get("event_type", "step"),
                    name=ev.get("name", "step"),
                    inputs=ev.get("inputs", {}),
                    outputs=ev.get("outputs", {}),
                    state_before=ev.get("state_before", {}),
                    state_after=ev.get("state_after", {}),
                    status=ev.get("status", "success"),
                    duration_ms=ev.get("duration_ms"),
                    error=ev.get("error"),
                    metadata=ev.get("metadata", {})
                )
                for ev in replay_trace
            ]
            db.save_events(events_to_save)

        return replay_trace
