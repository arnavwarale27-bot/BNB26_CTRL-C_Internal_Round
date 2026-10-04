from typing import Any, Dict, List, Optional
from .llm_diagnosis import LLMDiagnosisEngine


class UnifiedDiagnosis:
    """
    Unified AI & Rule-based Diagnostic facade.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.engine = LLMDiagnosisEngine(api_key=api_key)

    def diagnose(
        self,
        trace: List[Dict[str, Any]],
        expected_path: Optional[List[str]] = None,
        expected_output: Optional[Any] = None
    ) -> Dict[str, Any]:
        return self.engine.diagnose(
            trace=trace,
            expected_path=expected_path,
            expected_output=expected_output
        )
