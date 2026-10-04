from typing import List, Dict, Any
from .validator import ExecutionValidator
from .path_validator import ExecutionPathValidator


class UnifiedDiagnosis:
    def diagnose(
        self,
        trace: List[Dict[str, Any]],
        expected_path: List[str],
        expected_output: Any = None
    ) -> Dict[str, Any]:

        # 1. Check runtime failures
        failed_steps = [
            event for event in trace
            if event.get("status") == "failed"
        ]

        if failed_steps:
            failed = failed_steps[0]

            return {
                "status": "failure_detected",
                "failure_type": "runtime_failure",
                "root_cause": {
                    "step_id": failed.get("step_id"),
                    "name": failed.get("name"),
                    "error": failed.get("error")
                },
                "evidence": {
                    "runtime_failure": failed
                }
            }

        # 2. Check execution path
        path_result = ExecutionPathValidator().validate(
            trace,
            expected_path
        )

        if path_result["status"] != "passed":
            return {
                "status": "failure_detected",
                "failure_type": "path_mismatch",
                "root_cause": {
                    "step_id": None,
                    "name": path_result["actual_path"][-1]
                    if path_result["actual_path"] else None,
                    "error": "Execution path mismatch"
                },
                "evidence": {
                    "path_validation": path_result
                }
            }

        # 3. Check final output
        if expected_output is not None and trace:
            actual_output = trace[-1].get("outputs", {}).get("result")

            output_result = ExecutionValidator().validate(
                actual_output,
                expected_output
            )

            if not output_result["passed"]:
                return {
                    "status": "failure_detected",
                    "failure_type": "output_mismatch",
                    "root_cause": {
                        "step_id": trace[-1].get("step_id"),
                        "name": trace[-1].get("name"),
                        "error": "Output does not match expected result"
                    },
                    "evidence": {
                        "output_validation": output_result
                    }
                }

        # Everything passed
        return {
            "status": "success",
            "failure_type": None,
            "root_cause": None,
            "evidence": {}
        }
