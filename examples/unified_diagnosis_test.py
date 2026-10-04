from blackbox.database import TraceDatabase
from blackbox.unified_diagnosis import UnifiedDiagnosis
import pprint


TRACE_ID = "run_1f2543ba"

db = TraceDatabase()
trace = db.get_trace(TRACE_ID)

diagnosis = UnifiedDiagnosis().diagnose(
    trace=trace,
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
    }
)

print("\n=== UNIFIED DIAGNOSIS ===")
pprint.pp(diagnosis)
