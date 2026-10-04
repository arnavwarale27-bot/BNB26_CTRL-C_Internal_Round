from blackbox.coding_recorder import CodingRecorder


def main():

    print("=== AI CODING AGENT SIMULATION ===")

    recorder = CodingRecorder()

    try:
        recorder.read_file("examples/test_agent.py")
    except Exception:
        pass

    try:
        recorder.run_command(
            ["python", "examples/test_agent.py"]
        )
    except Exception:
        pass

    try:
        recorder.run_command(
            ["python", "-c", "raise Exception('Agent execution failed')"]
        )
    except Exception:
        pass

    print("\n=== BLACK BOX TRACE ===")

    trace = recorder.get_trace()

    for event in trace:

        print(
            event["step_id"],
            "|",
            event["event_type"],
            "|",
            event["name"],
            "|",
            event["status"]
        )

    print("\nTRACE ID:")
    print(recorder.recorder.trace_id)


if __name__ == "__main__":
    main()
