import json
from typing import Any, Dict, List, Optional
import openai

from .config import settings
from .validator import ExecutionValidator
from .path_validator import ExecutionPathValidator


DIAGNOSIS_SYSTEM_PROMPT = """You are Black Box, an expert observability judge and debugger for AI agent executions.
Analyze the provided chronological execution trace of an AI agent and produce a structured diagnosis of any failure or anomaly.

You must identify:
1. status: "success" if the agent executed correctly, or "failure_detected" if an error, anomaly, or mismatch occurred.
2. failure_type: A concise failure category (e.g., "runtime_failure", "invalid_tool_call", "llm_hallucination", "path_mismatch", "output_mismatch", "schema_validation_error").
3. root_cause: An object containing:
   - step_id: The exact step_id where the fault originated.
   - name: The name of the faulty step.
   - error: A technical description of why this step caused the failure.
4. evidence: Concrete observations from the inputs, outputs, error logs, or latency anomalies supporting your diagnosis.
5. explanation: A clear human-readable explanation of what happened, which step broke, and why.

Respond ONLY with valid JSON matching this exact structure:
{
  "status": "failure_detected",
  "failure_type": "string",
  "root_cause": {
    "step_id": "string",
    "name": "string",
    "error": "string"
  },
  "evidence": {
    "observed_input": "...",
    "observed_output_or_error": "...",
    "downstream_impact": "..."
  },
  "explanation": "..."
}
"""


class LLMDiagnosisEngine:
    """
    Real AI Diagnosis Engine using LLM-as-a-judge with deterministic fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model

    def diagnose_with_llm(
        self,
        trace: List[Dict[str, Any]],
        expected_path: Optional[List[str]] = None,
        expected_output: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Performs real LLM inference using the OpenAI SDK.
        """
        if not self.api_key:
            return None

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        trace_summary = {
            "total_steps": len(trace),
            "expected_path": expected_path,
            "expected_output": expected_output,
            "steps": [
                {
                    "step_id": s.get("step_id"),
                    "name": s.get("name"),
                    "event_type": s.get("event_type"),
                    "inputs": s.get("inputs"),
                    "outputs": s.get("outputs"),
                    "status": s.get("status"),
                    "duration_ms": s.get("duration_ms"),
                    "error": s.get("error"),
                    "state_before": s.get("state_before"),
                    "state_after": s.get("state_after"),
                }
                for s in trace
            ]
        }

        user_prompt = f"Execution Trace Data:\n{json.dumps(trace_summary, indent=2)}"

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = response.choices[0].message.content
            if content:
                parsed = json.loads(content)
                return parsed
        except Exception:
            return None

        return None

    def diagnose(
        self,
        trace: List[Dict[str, Any]],
        expected_path: Optional[List[str]] = None,
        expected_output: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Executes real AI LLM diagnosis when configured, falling back to deterministic trace analysis.
        """
        # 1. Try Real LLM Diagnosis
        llm_result = self.diagnose_with_llm(trace, expected_path, expected_output)
        if llm_result:
            return llm_result

        # 2. Deterministic Rule & Anomaly Analysis (when LLM key is absent)
        # Check for runtime exceptions
        failed_steps = [s for s in trace if s.get("status") == "failed"]
        if failed_steps:
            failed = failed_steps[0]
            error_msg = failed.get("error") or "Step execution failed with error"
            return {
                "status": "failure_detected",
                "failure_type": "runtime_failure",
                "root_cause": {
                    "step_id": failed.get("step_id"),
                    "name": failed.get("name"),
                    "error": error_msg
                },
                "evidence": {
                    "runtime_failure_event": failed
                },
                "explanation": f"Runtime failure occurred at step '{failed.get('name')}' (step_id: {failed.get('step_id')}). Error: {error_msg}"
            }

        # Check execution path
        if expected_path:
            path_result = ExecutionPathValidator().validate(trace, expected_path)
            if path_result["status"] != "passed":
                actual = path_result.get("actual_path", [])
                divergent_step = actual[-1] if actual else "start"
                return {
                    "status": "failure_detected",
                    "failure_type": "path_mismatch",
                    "root_cause": {
                        "step_id": trace[-1].get("step_id") if trace else None,
                        "name": divergent_step,
                        "error": f"Execution path diverged. Expected: {expected_path}, Actual: {actual}"
                    },
                    "evidence": {
                        "path_validation": path_result
                    },
                    "explanation": f"Agent execution diverged from the expected workflow path at step '{divergent_step}'. Missing: {path_result.get('missing_steps')}, Unexpected: {path_result.get('unexpected_steps')}."
                }

        # Check expected final output
        if expected_output is not None and trace:
            actual_output = trace[-1].get("outputs", {}).get("result")
            output_result = ExecutionValidator().validate(actual_output, expected_output)
            if not output_result.get("passed"):
                return {
                    "status": "failure_detected",
                    "failure_type": "output_mismatch",
                    "root_cause": {
                        "step_id": trace[-1].get("step_id"),
                        "name": trace[-1].get("name"),
                        "error": f"Final output '{actual_output}' did not match expected '{expected_output}'"
                    },
                    "evidence": {
                        "output_validation": output_result
                    },
                    "explanation": f"Agent completed all steps, but the final output '{actual_output}' did not match expected value '{expected_output}'."
                }

        # Everything passed
        return {
            "status": "success",
            "failure_type": None,
            "root_cause": None,
            "evidence": {},
            "explanation": "All execution steps, invariants, and output validations completed successfully with zero anomalies."
        }
