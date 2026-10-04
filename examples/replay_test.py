from blackbox.database import TraceDatabase
from blackbox.replay import ReplayEngine
import pprint


def count_cities(data):
    return {
        "Mumbai": data.count("Mumbai"),
        "Pune": data.count("Pune"),
        "Nashik": data.count("Nashik")
    }


TRACE_ID = "run_3988a655"
CHECKPOINT = "step_847100a4"

trace = TraceDatabase().get_trace(TRACE_ID)


modified_data = [
    "Mumbai",
    "Mumbai",
    "Mumbai",
    "Pune",
    "Nashik"
]


downstream_functions = {
    "count_cities": count_cities
}


replay = ReplayEngine().replay(
    trace=trace,
    checkpoint_step_id=CHECKPOINT,
    modified_output=modified_data,
    downstream_functions=downstream_functions
)


print("\n=== ORIGINAL TRACE ===")
pprint.pp(trace)

print("\n=== REPLAYED TRACE ===")
pprint.pp(replay)
