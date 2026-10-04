from typing import Any, Dict, List


class ExecutionHistory:

    def build(
        self,
        trace: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        history = []

        for index, event in enumerate(trace, start=1):

            result = event.get(
                "outputs",
                {}
            ).get(
                "result",
                {}
            )

            history.append({
                "step_number": index,
                "step_id": event.get("step_id"),
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "name": event.get("name"),
                "status": event.get("status"),
                "input": event.get("inputs", {}),
                "output": result,
                "error": event.get("error"),
                "duration_ms": event.get("duration_ms")
            })

        return history
