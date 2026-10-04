import re
from typing import Any, Dict


class ErrorDetails:

    def extract(
        self,
        trace_event: Dict[str, Any]
    ) -> Dict[str, Any]:

        error = trace_event.get("error", "")

        outputs = trace_event.get(
            "outputs",
            {}
        )

        result = outputs.get(
            "result",
            {}
        )

        exit_code = result.get(
            "exit_code"
        )

        stderr = result.get(
            "stderr",
            ""
        )

        # Use the stored error first.
        # If it is empty, use stderr.
        error_text = error or stderr

        if not error_text:

            return {
                "has_error": False,
                "error_type": None,
                "message": None,
                "location": None,
                "exit_code": exit_code,
                "stack_trace": None
            }

        # -----------------------------------------
        # ERROR TYPE
        # -----------------------------------------

        error_type = "Runtime Error"

        match = re.search(
            r"(?:Exception|Error):\s*(.*)",
            error_text
        )

        message = None

        if match:
            message = match.group(1).strip()

        # -----------------------------------------
        # LOCATION
        # -----------------------------------------

        location = None

        location_match = re.search(
            r'File "([^"]+)", line (\d+)',
            error_text
        )

        if location_match:

            location = {
                "file": location_match.group(1),
                "line": int(location_match.group(2))
            }

        # -----------------------------------------
        # RETURN STRUCTURED ERROR
        # -----------------------------------------

        return {
            "has_error": True,
            "error_type": error_type,
            "message": message or error_text,
            "location": location,
            "exit_code": exit_code,
            "stack_trace": error_text
        }
