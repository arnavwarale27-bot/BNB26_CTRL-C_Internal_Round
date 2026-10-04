from typing import List, Dict, Any


class TraceComparator:
    """
    Compares original execution with a replayed execution.
    """

    def compare(
        self,
        original_trace: List[Dict[str, Any]],
        replay_trace: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        differences = []
        checkpoint = None

        original_by_step = {
            event["step_id"]: event
            for event in original_trace
        }

        replay_by_step = {
            event["step_id"]: event
            for event in replay_trace
        }

        for step_id, replay_event in replay_by_step.items():

            original_event = original_by_step.get(step_id)

            if not original_event:
                differences.append({
                    "step_id": step_id,
                    "type": "new_step",
                    "replay": replay_event
                })
                continue

            original_output = original_event.get(
                "outputs", {}
            ).get("result")

            replay_output = replay_event.get(
                "outputs", {}
            ).get("result")

            if original_output != replay_output:

                if replay_event.get("metadata", {}).get("checkpoint"):
                    checkpoint = {
                        "step_id": step_id,
                        "name": replay_event.get("name"),
                        "original_output": original_output,
                        "modified_output": replay_output
                    }

                else:
                    differences.append({
                        "step_id": step_id,
                        "name": replay_event.get("name"),
                        "type": "downstream_effect",
                        "original_output": original_output,
                        "replay_output": replay_output
                    })

        return {
            "status": "different"
            if checkpoint or differences
            else "identical",

            "checkpoint": checkpoint,

            "downstream_effects": differences
        }
