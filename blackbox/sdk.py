import contextvars
import dataclasses
import functools
import inspect
import json
import time
import uuid
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import httpx

from .config import settings
from .models import GenericSpan

# Context variables to track execution span hierarchies across arbitrary nested calls
_current_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_trace_id", default=None
)
_current_parent_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_parent_span_id", default=None
)

# Global registry of traced functions for dynamic in-process replay
_traced_functions: Dict[str, Callable] = {}


def safe_serialize(obj: Any, depth: int = 0, max_depth: int = 5) -> Any:
    """
    Recursively and safely converts any arbitrary Python object into a JSON-serializable structure.
    Handles dataclasses, Pydantic models, dicts, iterables, and custom objects using inspect.
    """
    if depth > max_depth:
        return str(obj)

    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")

    # Pydantic v2 / v1
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return safe_serialize(obj.model_dump(mode="json"), depth + 1, max_depth)
        except Exception:
            pass

    if hasattr(obj, "dict") and callable(obj.dict):
        try:
            return safe_serialize(obj.dict(), depth + 1, max_depth)
        except Exception:
            pass

    # Dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        try:
            return safe_serialize(dataclasses.asdict(obj), depth + 1, max_depth)
        except Exception:
            pass

    # Standard containers
    if isinstance(obj, dict):
        return {str(k): safe_serialize(v, depth + 1, max_depth) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [safe_serialize(item, depth + 1, max_depth) for item in obj]

    # Custom class instances / objects
    if hasattr(obj, "__dict__"):
        try:
            return {
                k: safe_serialize(v, depth + 1, max_depth)
                for k, v in vars(obj).items()
                if not k.startswith("_")
            }
        except Exception:
            pass

    return str(obj)


class UniversalBlackBoxSDK:
    """
    Universal, framework-agnostic telemetry tracer for any arbitrary Python code.
    """

    def __init__(self, api_url: Optional[str] = None, timeout: float = 2.0):
        self.api_url = api_url or settings.api_url
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def new_trace(self, trace_id: Optional[str] = None) -> str:
        tid = trace_id or f"trace_{uuid.uuid4().hex[:8]}"
        _current_trace_id.set(tid)
        _current_parent_span_id.set(None)
        return tid

    def get_current_trace_id(self) -> str:
        tid = _current_trace_id.get()
        if not tid:
            tid = self.new_trace()
        return tid

    def emit_span(self, span: GenericSpan):
        """
        Sends a generic span payload over real HTTP to the backend DAG storage.
        """
        try:
            url = f"{self.api_url.rstrip('/')}/traces/ingest"
            payload = {"spans": [span.model_dump(mode="json")]}
            self._client.post(url, json=payload)
        except Exception:
            # Graceful degradation: telemetry never interrupts core execution
            pass

    def trace(self, func_or_name: Any = None, **decorator_kwargs):
        """
        Universal @blackbox.trace decorator.
        Works seamlessly as `@blackbox.trace` or `@blackbox.trace(name="custom_name")`.
        Captures dynamic *args, **kwargs, inspects argument names, outputs, durations, and nested parent spans.
        """
        def make_decorator(target_name: Optional[str] = None):
            def decorator(func: Callable):
                func_name = target_name or func.__name__
                _traced_functions[func_name] = func
                _traced_functions[func.__qualname__] = func

                sig = inspect.signature(func)

                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    trace_id = self.get_current_trace_id()
                    span_id = f"span_{uuid.uuid4().hex[:8]}"
                    parent_span_id = _current_parent_span_id.get()

                    # Set current span as parent for any downstream nested calls
                    token = _current_parent_span_id.set(span_id)

                    # Inspect and bind arguments to their declared parameter names
                    inputs_map: Dict[str, Any] = {}
                    try:
                        bound = sig.bind(*args, **kwargs)
                        bound.apply_defaults()
                        inputs_map = safe_serialize(dict(bound.arguments))
                    except Exception:
                        inputs_map = {
                            "args": safe_serialize(list(args)),
                            "kwargs": safe_serialize(dict(kwargs))
                        }

                    start_time = time.perf_counter()
                    status = "success"
                    error_msg = None
                    output_val: Any = None

                    try:
                        result = func(*args, **kwargs)
                        output_val = safe_serialize(result)
                        return result
                    except Exception as ex:
                        status = "failed"
                        error_msg = f"{type(ex).__name__}: {str(ex)}"
                        output_val = {"error": error_msg}
                        raise ex
                    finally:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0

                        span = GenericSpan(
                            trace_id=trace_id,
                            span_id=span_id,
                            parent_span_id=parent_span_id,
                            function_name=func_name,
                            inputs=inputs_map if isinstance(inputs_map, dict) else {"data": inputs_map},
                            outputs={"result": output_val} if not isinstance(output_val, dict) else output_val,
                            locals={},
                            timestamp=datetime.now(timezone.utc),
                            duration_ms=round(duration_ms, 2),
                            status=status,
                            error=error_msg,
                            metadata={
                                "module": func.__module__,
                                "qualname": func.__qualname__
                            }
                        )

                        self.emit_span(span)
                        _current_parent_span_id.reset(token)

                return sync_wrapper

            return decorator

        if callable(func_or_name):
            # Used as @blackbox.trace without arguments
            return make_decorator(None)(func_or_name)
        elif isinstance(func_or_name, str):
            # Used as @blackbox.trace("custom_name")
            return make_decorator(func_or_name)
        else:
            # Used as @blackbox.trace(name="custom_name")
            return make_decorator(decorator_kwargs.get("name"))


blackbox = UniversalBlackBoxSDK()
trace = blackbox.trace
new_trace = blackbox.new_trace
get_current_trace_id = blackbox.get_current_trace_id


def get_registered_function(name: str) -> Optional[Callable]:
    return _traced_functions.get(name)
