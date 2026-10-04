from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GenericSpan(BaseModel):
    """
    Universal OpenTelemetry-aligned Span model for arbitrary Python code execution DAGs.
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    function_name: str

    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    locals: Dict[str, Any] = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None
    status: str = "success"  # success | failed | running
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Backward-compatibility alias
TraceEvent = GenericSpan


class IngestSpansRequest(BaseModel):
    events: Optional[List[GenericSpan]] = None
    spans: Optional[List[GenericSpan]] = None


class GenericReplayRequest(BaseModel):
    trace_id: str
    checkpoint_span_id: str
    modified_inputs: Optional[Dict[str, Any]] = None
    modified_output: Optional[Any] = None
    entrypoint_command: Optional[List[str]] = None


# Backward-compatibility alias
ReplayRequest = GenericReplayRequest
