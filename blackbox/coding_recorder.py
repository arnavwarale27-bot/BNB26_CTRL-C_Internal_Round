import os
import subprocess
import time
from typing import Any, Dict, Optional

from .recorder import BlackBoxRecorder


class CodingRecorder:

    def __init__(
        self,
        recorder: Optional[BlackBoxRecorder] = None
    ):

        self.recorder = recorder or BlackBoxRecorder()

    # -----------------------------------------
    # READ FILE
    # -----------------------------------------

    def read_file(self, path: str) -> Dict[str, Any]:

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                content = file.read()

            result = {
                "path": path,
                "size": len(content),
                "lines": len(content.splitlines())
            }

            with self.recorder.trace(
                name="read_file",
                event_type="file_read",
                inputs={
                    "path": path
                }
            ) as step:

                step.set_output(result)

            return result

        except Exception as error:

            with self.recorder.trace(
                name="read_file",
                event_type="file_read",
                inputs={
                    "path": path
                }
            ) as step:

                step.set_output({})

                step.set_error(str(error))

            raise

    # -----------------------------------------
    # WRITE FILE
    # -----------------------------------------

    def write_file(
        self,
        path: str,
        content: str
    ) -> Dict[str, Any]:

        old_content = ""

        try:

            if os.path.exists(path):

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    old_content = file.read()

            with open(
                path,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(content)

            result = {
                "path": path,
                "old_size": len(old_content),
                "new_size": len(content),
                "changed": old_content != content
            }

            with self.recorder.trace(
                name="write_file",
                event_type="file_write",
                inputs={
                    "path": path
                },
                metadata={
                    "operation": "write_file"
                }
            ) as step:

                step.set_output(result)

                step.set_state_before({
                    "content_size": len(old_content)
                })

                step.set_state_after({
                    "content_size": len(content)
                })

            return result

        except Exception as error:

            with self.recorder.trace(
                name="write_file",
                event_type="file_write",
                inputs={
                    "path": path
                }
            ) as step:

                step.set_output({})

                step.set_error(str(error))

            raise

    # -----------------------------------------
    # RUN COMMAND
    # -----------------------------------------

    def run_command(
        self,
        command: list[str],
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:

        start_time = time.time()

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd
            )

            duration_ms = round(
                (time.time() - start_time) * 1000,
                2
            )

            program_status = (
                "success"
                if result.returncode == 0
                else "failed"
            )

            event_result = {
                "command": command,
                "cwd": cwd,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "duration_ms": duration_ms
            }

            with self.recorder.trace(
                name="run_command",
                event_type="command_execution",
                inputs={
                    "command": command,
                    "cwd": cwd
                },
                metadata={
                    "program_status": program_status
                }
            ) as step:

                step.set_output(event_result)

                if result.returncode != 0:

                    step.set_state_after({
                        "exit_code": result.returncode,
                        "failed": True
                    })

                    # IMPORTANT:
                    # subprocess itself ran successfully,
                    # but the program being executed failed.
                    step.set_error(
                        result.stderr.strip()
                        or f"Command failed with exit code {result.returncode}"
                    )

                else:

                    step.set_state_after({
                        "exit_code": 0,
                        "failed": False
                    })

            return event_result

        except Exception as error:

            with self.recorder.trace(
                name="run_command",
                event_type="command_execution",
                inputs={
                    "command": command,
                    "cwd": cwd
                }
            ) as step:

                step.set_output({})

                step.set_error(str(error))

            raise

    # -----------------------------------------
    # RUN TEST
    # -----------------------------------------

    def run_test(
        self,
        command: list[str],
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:

        result = self.run_command(
            command=command,
            cwd=cwd
        )

        result["test"] = True

        return result

    # -----------------------------------------
    # GET TRACE HISTORY
    # -----------------------------------------

    def get_trace(self):

        return self.recorder.db.get_trace(
            self.recorder.trace_id
        )
