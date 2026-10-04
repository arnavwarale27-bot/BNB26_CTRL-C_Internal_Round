from blackbox.database import TraceDatabase
from blackbox.replay import ReplayEngine
from blackbox.comparator import TraceComparator
import pprint


def count_cities(data):
    return {
        "Mumbai": data.count("Mumbai"),
        "Pune": data.count("Pune"),
        "Nashik": data.count("Nashik")
    }


TRACE_ID = "run_3988a655"
CHECKPOINT = "step_847100a4"

db = TraceDatabase()

original_trace = db.get_trace(TRACE_ID)

modified_data = [
    "Mumbai",
    "Mumbai",
    "Mumbai",
    "Pune",
    "Nashik"
]

replay_trace = ReplayEngine().replay(
    trace=original_trace,
    checkpoint_step_id=CHECKPOINT,
    modified_output=modified_data,
    downstream_functions={
        "count_cities": count_cities
    }
)

comparison = TraceComparator().compare(
    original_trace,
    replay_trace
)

print("\n=== ORIGINAL vs REPLAY ===")
pprint.pp(comparison)
