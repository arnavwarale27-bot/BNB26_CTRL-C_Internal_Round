from typing import Any, Dict


class ExecutionValidator:
    """
    Compares the expected result of an agent step
    with the actual recorded result.
    """

    def validate(
        self,
        actual_output: Any,
        expected_output: Any
    ) -> Dict:

        if actual_output == expected_output:
            return {
                "status": "passed",
                "message": "Actual output matches expected output.",
                "expected": expected_output,
                "actual": actual_output
            }

        return {
            "status": "mismatch",
            "message": "Actual output does not match expected output.",
            "expected": expected_output,
            "actual": actual_output
        }
