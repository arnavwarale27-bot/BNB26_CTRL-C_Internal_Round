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

    raise ValueError("Invalid city data")


data = read_data()

try:
    count_cities(data)
except Exception as error:
    print("Agent error:")
    print(error)

print("\nTrace ID:")
print(recorder.trace_id)
