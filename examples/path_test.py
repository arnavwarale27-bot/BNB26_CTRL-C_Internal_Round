from blackbox.database import TraceDatabase
from blackbox.path_validator import ExecutionPathValidator
import pprint


TRACE_ID = "run_1f2543ba"

trace = TraceDatabase().get_trace(TRACE_ID)

expected_path = [
    "read_data",
    "create_pivot_table"
]

result = ExecutionPathValidator().validate(
    trace,
    expected_path
)

print("\n=== EXECUTION PATH VALIDATION ===")
pprint.pp(result)
