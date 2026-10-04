from blackbox.database import TraceDatabase
from blackbox.ground_truth import GroundTruth
from blackbox.diagnosis import FailureDiagnosis
from blackbox.explanation import FailureExplanation
import pprint


TRACE_ID = "run_1f2543ba"

trace = TraceDatabase().get_trace(TRACE_ID)


ground_truth = GroundTruth(
    goal="Create a pivot table showing cities",

    expected_path=[
        "read_data",
        "select_city_column",
        "create_pivot_table",
        "verify_result"
    ],

    expected_output={
        "Mumbai": 2,
        "Pune": 2,
        "Nashik": 1
    },

    constraints=[
        "Must create a pivot table",
        "Must use the city column",
        "Must verify the final result"
    ]
)


diagnosis = FailureDiagnosis().diagnose(
    trace,
    ground_truth.to_dict()
)

explanation = FailureExplanation().explain(diagnosis)


print("\n=== GROUND TRUTH ===")
pprint.pp(ground_truth.to_dict())

print("\n=== DIAGNOSIS ===")
pprint.pp(diagnosis)

print("\n=== EXPLANATION ===")
print(explanation)
