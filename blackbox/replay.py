from typing import Any, Callable, Dict, List


class ReplayEngine:
    """
    Checkpoint replay engine.

    Replaces the output of a selected checkpoint and
    re-executes downstream functions.
    """

    def replay(
        self,
        trace: List[Dict[str, Any]],
        checkpoint_step_id: str,
        modified_output: Any,
        downstream_functions: Dict[str, Callable]
    ) -> List[Dict[str, Any]]:

        checkpoint_found = False
        replay_trace = []

        current_output = None

        for event in trace:

            step_id = event["step_id"]
            name = event["name"]

            # Before checkpoint: use original cached result
            if not checkpoint_found:

                if step_id == checkpoint_step_id:

                    checkpoint_found = True
                    current_output = modified_output

                    replay_event = event.copy()

                    replay_event["outputs"] = {
                        "result": modified_output
                    }

                    replay_event["metadata"] = {
                        **event.get("metadata", {}),
                        "replayed": True,
                        "checkpoint": True
                    }

                    replay_trace.append(replay_event)

                continue

            # After checkpoint: re-run downstream function
            function = downstream_functions.get(name)

            if function is None:
                continue

            try:

                result = function(current_output)

                current_output = result

                replay_event = event.copy()

                replay_event["outputs"] = {
                    "result": result
                }

                replay_event["status"] = "success"

                replay_event["metadata"] = {
                    **event.get("metadata", {}),
                    "replayed": True,
                    "checkpoint": False
                }

                replay_trace.append(replay_event)

            except Exception as error:

                replay_event = event.copy()

                replay_event["outputs"] = {
                    "result": {}
                }

                replay_event["status"] = "failed"
                replay_event["error"] = str(error)

                replay_event["metadata"] = {
                    **event.get("metadata", {}),
                    "replayed": True
                }

                replay_trace.append(replay_event)

                break

        if not checkpoint_found:
            raise ValueError(
                f"Checkpoint '{checkpoint_step_id}' "
                f"was not found in the trace."
            )

        return replay_trace
