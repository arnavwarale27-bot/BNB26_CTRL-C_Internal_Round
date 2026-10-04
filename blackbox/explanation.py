class FailureExplanation:

    def explain(self, diagnosis):

        if diagnosis.get("status") == "success":
            return "No failure detected."

        failure_type = diagnosis.get("failure_type")
        root_cause = diagnosis.get("root_cause", {})
        evidence = diagnosis.get("evidence", {})

        # Runtime failure
        if failure_type == "runtime_failure":
            error = root_cause.get("error", "Unknown error")

            return (
                f"The step '{root_cause.get('name')}' failed during execution. "
                f"Error: {error}."
            )

        # Execution path mismatch
        if failure_type == "path_mismatch":

            path_validation = evidence.get("path_validation", {})

            expected = path_validation.get("expected_path", [])
            actual = path_validation.get("actual_path", [])
            missing = path_validation.get("missing_steps", [])
            unexpected = path_validation.get("unexpected_steps", [])

            return (
                "The agent completed execution, but followed an unexpected "
                "execution path.\n\n"
                f"Expected path: {' → '.join(expected)}\n"
                f"Actual path: {' → '.join(actual)}\n\n"
                f"Missing steps: {', '.join(missing) if missing else 'None'}\n"
                f"Unexpected steps: {', '.join(unexpected) if unexpected else 'None'}\n\n"
                f"The execution diverged at '{root_cause.get('name')}'."
            )

        # Output mismatch
        if failure_type == "output_mismatch":

            output_validation = evidence.get("output_validation", {})

            expected = output_validation.get("expected")
            actual = output_validation.get("actual")

            return (
                f"The step '{root_cause.get('name')}' produced an unexpected "
                f"output.\n\n"
                f"Expected: {expected}\n"
                f"Actual: {actual}"
            )

        return (
            f"The step '{root_cause.get('name')}' was identified as the "
            "root cause of the failure."
        )
