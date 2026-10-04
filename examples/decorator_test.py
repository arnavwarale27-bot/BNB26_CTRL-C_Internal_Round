from blackbox.recorder import BlackBoxRecorder
from blackbox.tracer import trace_node


recorder = BlackBoxRecorder()


@trace_node(
    recorder,
    name="read_data",
    event_type="tool_call"
)
def read_data():
    return [
        "Mumbai",
        "Pune",
        "Mumbai",
        "Nashik",
        "Pune"
    ]


@trace_node(
    recorder,
    name="count_cities",
    event_type="tool_call"
)
def count_cities(data):
    return {
        "Mumbai": data.count("Mumbai"),
        "Pune": data.count("Pune"),
        "Nashik": data.count("Nashik")
    }


data = read_data()
result = count_cities(data)

print("Result:")
print(result)

print("\nTrace ID:")
print(recorder.trace_id)
