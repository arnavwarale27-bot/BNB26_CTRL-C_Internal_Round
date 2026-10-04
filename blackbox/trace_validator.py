from typing import Dict, Any

from .validator import ExecutionValidator


class TraceValidator:

    def validate_step(
        self,
        trace_event: Dict[str, Any],
        expected_output: Any
    ) -> Dict[str, Any]:

        actual_output = trace_event.get("outputs", {}).get("result")

        result = ExecutionValidator().validate(
            actual_output,
            expected_output
        )

        return {
            "step_id": trace_event.get("step_id"),
            "step_name": trace_event.get("name"),
            **result
        }
