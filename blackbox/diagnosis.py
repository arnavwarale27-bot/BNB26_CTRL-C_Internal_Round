from typing import List, Dict


class FailureDiagnosis:
    """
    Diagnosis engine for Black Box.

    Evaluates an agent trace against ground truth.
    """

    def diagnose(
        self,
        trace: List[Dict],
        ground_truth: Dict
    ) -> Dict:

        expected_path = ground_truth.get("expected_path", [])

        actual_path = [
            event.get("name")
            for event in trace
        ]

        # Check runtime failures
        failed_steps = [
            event for event in trace
            if event.get("status") == "failed"
        ]

        if failed_steps:
            root = failed_steps[0]

            return {
                "status": "failure_detected",
                "failure_type": "execution_failure",
                "message": "Execution failure detected.",
                "root_cause": {
                    "step_id": root["step_id"],
                    "name": root["name"],
                    "error": root["error"]
                },
                "evidence": [
                    {
                        "step_id": root["step_id"],
                        "name": root["name"],
                        "status": "failed",
                        "error": root["error"]
                    }
                ]
            }

        # Check execution path
        if actual_path != expected_path:

            missing_steps = [
                step for step in expected_path
                if step not in actual_path
            ]

            unexpected_steps = [
                step for step in actual_path
                if step not in expected_path
            ]

            divergence_step = None

            for expected, actual in zip(expected_path, actual_path):
                if expected != actual:
                    divergence_step = actual
                    break

            if divergence_step is None and len(actual_path) < len(expected_path):
                divergence_step = actual_path[-1] if actual_path else None

            return {
                "status": "failure_detected",
                "failure_type": "path_mismatch",
                "message": (
                    "Agent completed execution, "
                    "but followed an unexpected execution path."
                ),
                "root_cause": {
                    "step_id": None,
                    "name": divergence_step,
                    "error": "Execution path mismatch"
                },
                "evidence": [
                    {
                        "status": "path_mismatch",
                        "expected_path": expected_path,
                        "actual_path": actual_path,
                        "missing_steps": missing_steps,
                        "unexpected_steps": unexpected_steps
                    }
                ]
            }

        # Everything matches
        return {
            "status": "success",
            "failure_type": None,
            "message": "Agent execution matches the expected task.",
            "root_cause": None,
            "evidence": []
        }
