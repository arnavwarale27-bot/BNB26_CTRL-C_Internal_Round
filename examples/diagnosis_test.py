from blackbox.database import TraceDatabase
from blackbox.diagnosis import FailureDiagnosis
from blackbox.explanation import FailureExplanation
import pprint


TRACE_ID = "run_713ebd8f"


trace = TraceDatabase().get_trace(TRACE_ID)

diagnosis = FailureDiagnosis().diagnose(trace)

explanation = FailureExplanation().explain(diagnosis)


print("\n=== BLACK BOX DIAGNOSIS ===")

print("\nDiagnosis:")
pprint.pp(diagnosis)

print("\nExplanation:")
print(explanation)
