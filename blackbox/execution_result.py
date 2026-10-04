from typing import Any, Dict, List

from .error_details import ErrorDetails
from .history import ExecutionHistory


class ExecutionResult:

    def build(
        self,
        trace: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        if not trace:
            return {
                "status": "no_execution",
                "input": None,
                "output": None,
                "error": None,
                "history": []
            }

        history = ExecutionHistory().build(trace)

        last_event = trace[-1]

        last_result = last_event.get(
            "outputs",
            {}
        ).get(
            "result",
            {}
        )

        status = last_event.get(
            "status",
            "unknown"
        )

        result = {
            "status": status,

            "input": last_event.get(
                "inputs",
                {}
            ),

            "output": {
                "stdout": last_result.get(
                    "stdout",
                    ""
                ),

                "stderr": last_result.get(
                    "stderr",
                    ""
                ),

                "exit_code": last_result.get(
                    "exit_code"
                )
            },

            "error": None,

            "history": history
        }

        # -----------------------------------------
        # ERROR DETAILS
        # -----------------------------------------

        if status == "failed":

            result["error"] = ErrorDetails().extract(
                last_event
            )

        return result
