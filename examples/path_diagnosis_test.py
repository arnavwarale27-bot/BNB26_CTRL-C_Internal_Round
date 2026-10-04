from blackbox.database import TraceDatabase
from blackbox.path_validator import ExecutionPathValidator
from blackbox.diagnosis import FailureDiagnosis
from blackbox.explanation import FailureExplanation
import pprint


TRACE_ID = "run_1f2543ba"

trace = TraceDatabase().get_trace(TRACE_ID)

expected_path = [
    "read_data",
    "create_pivot_table"
]

path_validation = ExecutionPathValidator().validate(
    trace,
    expected_path
)

diagnosis = FailureDiagnosis().diagnose(
    trace,
    path_validation=path_validation
)

explanation = FailureExplanation().explain(diagnosis)


print("\n=== PATH VALIDATION ===")
pprint.pp(path_validation)

print("\n=== BLACK BOX DIAGNOSIS ===")
pprint.pp(diagnosis)

print("\n=== EXPLANATION ===")
print(explanation)
