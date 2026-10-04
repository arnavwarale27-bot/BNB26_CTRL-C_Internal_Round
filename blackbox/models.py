from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """
    A single observable event during an AI agent execution.
    """

    trace_id: str
    step_id: str

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    event_type: str
    name: str

    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)

    state_before: Dict[str, Any] = Field(default_factory=dict)
    state_after: Dict[str, Any] = Field(default_factory=dict)

    status: str = "success"

    duration_ms: Optional[float] = None

    error: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
