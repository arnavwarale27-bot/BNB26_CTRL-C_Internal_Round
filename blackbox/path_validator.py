from typing import List, Dict


class ExecutionPathValidator:
    """
    Validates whether an agent followed the expected execution path.
    """

    def validate(
        self,
        trace: List[Dict],
        expected_steps: List[str]
    ) -> Dict:

        actual_steps = [
            event.get("name")
            for event in trace
        ]

        missing_steps = [
            step for step in expected_steps
            if step not in actual_steps
        ]

        unexpected_steps = [
            step for step in actual_steps
            if step not in expected_steps
        ]

        path_matches = actual_steps == expected_steps

        return {
            "status": "passed" if path_matches else "path_mismatch",
            "expected_path": expected_steps,
            "actual_path": actual_steps,
            "missing_steps": missing_steps,
            "unexpected_steps": unexpected_steps,
            "message": (
                "Execution path matches expected path."
                if path_matches
                else "Agent execution path does not match expected path."
            )
        }
