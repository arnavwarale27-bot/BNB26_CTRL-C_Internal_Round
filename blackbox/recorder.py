import time
import uuid
from contextlib import contextmanager

from .database import TraceDatabase
from .models import TraceEvent


class TraceStep:

    def __init__(self, name, event_type):
        self.name = name
        self.event_type = event_type
        self.output = {}
        self.state_before = {}
        self.state_after = {}
        self.error = None

    def set_output(self, output):
        self.output = output

    def set_state_before(self, state):
        self.state_before = state

    def set_state_after(self, state):
        self.state_after = state

    def set_error(self, error):
        self.error = error


class BlackBoxRecorder:

    def __init__(self, trace_id=None, db_path="blackbox.db"):

        self.trace_id = trace_id or f"run_{uuid.uuid4().hex[:8]}"

        self.db = TraceDatabase(db_path)

    @contextmanager
    def trace(
        self,
        name,
        event_type="execution",
        inputs=None,
        metadata=None
    ):

        step_id = f"step_{uuid.uuid4().hex[:8]}"

        start_time = time.time()

        step = TraceStep(
            name=name,
            event_type=event_type
        )

        try:

            yield step

            duration_ms = round(
                (time.time() - start_time) * 1000,
                2
            )

            # If the step recorded an error,
            # mark the event as failed.
            if step.error:
                status = "failed"
            else:
                status = "success"

            event = TraceEvent(
                trace_id=self.trace_id,
                step_id=step_id,
                event_type=event_type,
                name=name,
                inputs=inputs or {},
                outputs={
                    "result": step.output
                },
                state_before=step.state_before,
                state_after=step.state_after,
                status=status,
                duration_ms=duration_ms,
                error=step.error,
                metadata=metadata or {}
            )

            self.db.save_event(event)

        except Exception as error:

            duration_ms = round(
                (time.time() - start_time) * 1000,
                2
            )

            event = TraceEvent(
                trace_id=self.trace_id,
                step_id=step_id,
                event_type=event_type,
                name=name,
                inputs=inputs or {},
                outputs={
                    "result": step.output
                },
                state_before=step.state_before,
                state_after=step.state_after,
                status="failed",
                duration_ms=duration_ms,
                error=str(error),
                metadata=metadata or {}
            )

            self.db.save_event(event)

            raise
