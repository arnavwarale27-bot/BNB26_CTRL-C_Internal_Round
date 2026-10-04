from typing import List, Dict, Any


class GroundTruth:

    def __init__(
        self,
        goal: str,
        expected_path: List[str],
        expected_output: Any = None,
        constraints: List[str] = None
    ):
        self.goal = goal
        self.expected_path = expected_path
        self.expected_output = expected_output
        self.constraints = constraints or []

    def to_dict(self) -> Dict:
        return {
            "goal": self.goal,
            "expected_path": self.expected_path,
            "expected_output": self.expected_output,
            "constraints": self.constraints
        }
