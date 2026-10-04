from blackbox.recorder import BlackBoxRecorder


def read_data():
    return ["Mumbai", "Pune", "Mumbai", "Nashik", "Pune"]


def count_cities_wrong(data):
    # Simulate an agent making a mistake
    return {
        "Mumbai": 2,
        "Pune": 1
    }


def main():
    recorder = BlackBoxRecorder()

    with recorder.trace(
        "read_data",
        event_type="tool_call"
    ) as step:
        data = read_data()
        step.set_output(data)

    with recorder.trace(
        "count_cities",
        event_type="tool_call",
        inputs={"rows": len(data)}
    ) as step:
        result = count_cities_wrong(data)
        step.set_output(result)

    print("Agent result:")
    print(result)

    print("\nTrace ID:")
    print(recorder.trace_id)


if __name__ == "__main__":
    main()
