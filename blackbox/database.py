import json
import sqlite3
from typing import Any, Dict, List, Optional

from .config import settings
from .models import GenericSpan


class GenericTraceDatabase:
    """
    Generic SQLite storage for arbitrary execution DAGs (spans and parent-child edges).
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.db_path
        self._create_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_spans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                span_id TEXT NOT NULL,
                parent_span_id TEXT,
                function_name TEXT NOT NULL,
                inputs_json TEXT,
                outputs_json TEXT,
                locals_json TEXT,
                timestamp TEXT NOT NULL,
                duration_ms REAL,
                status TEXT NOT NULL,
                error TEXT,
                metadata TEXT
            )
            """
        )

        # Index for fast DAG querying by trace_id and parent_span_id
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trace_id ON execution_spans(trace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_span_id ON execution_spans(span_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_span ON execution_spans(parent_span_id)")

        connection.commit()
        connection.close()

    def save_span(self, span: GenericSpan):
        connection = self._connect()
        cursor = connection.cursor()

        timestamp_str = (
            span.timestamp.isoformat()
            if hasattr(span.timestamp, "isoformat")
            else str(span.timestamp)
        )

        cursor.execute(
            """
            INSERT INTO execution_spans (
                trace_id,
                span_id,
                parent_span_id,
                function_name,
                inputs_json,
                outputs_json,
                locals_json,
                timestamp,
                duration_ms,
                status,
                error,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.trace_id,
                span.span_id,
                span.parent_span_id,
                span.function_name,
                json.dumps(span.inputs or {}),
                json.dumps(span.outputs or {}),
                json.dumps(span.locals or {}),
                timestamp_str,
                span.duration_ms,
                span.status,
                span.error,
                json.dumps(span.metadata or {}),
            ),
        )

        connection.commit()
        connection.close()

    def save_spans(self, spans: List[GenericSpan]):
        for span in spans:
            self.save_span(span)

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all DAG span nodes for a trace in chronological sequence.
        """
        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                trace_id,
                span_id,
                parent_span_id,
                function_name,
                inputs_json,
                outputs_json,
                locals_json,
                timestamp,
                duration_ms,
                status,
                error,
                metadata
            FROM execution_spans
            WHERE trace_id = ?
            ORDER BY id ASC
            """,
            (trace_id,),
        )

        rows = cursor.fetchall()
        connection.close()

        spans = []
        for row in rows:
            spans.append(
                {
                    "trace_id": row[0],
                    "span_id": row[1],
                    "step_id": row[1],  # Backward-compatible alias
                    "parent_span_id": row[2],
                    "parent_step_id": row[2],
                    "function_name": row[3],
                    "name": row[3],  # Backward-compatible alias
                    "inputs": json.loads(row[4] or "{}"),
                    "outputs": json.loads(row[5] or "{}"),
                    "locals": json.loads(row[6] or "{}"),
                    "timestamp": row[7],
                    "duration_ms": row[8],
                    "status": row[9],
                    "error": row[10],
                    "metadata": json.loads(row[11] or "{}"),
                }
            )

        return spans

    def list_traces(self) -> List[Dict[str, Any]]:
        """
        Aggregates high-level trace executions from stored DAG nodes.
        """
        connection = self._connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                trace_id,
                MIN(timestamp),
                COUNT(*),
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END),
                SUM(COALESCE(duration_ms, 0))
            FROM execution_spans
            GROUP BY trace_id
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()
        connection.close()

        return [
            {
                "trace_id": row[0],
                "timestamp": row[1],
                "total_steps": row[2],
                "total_spans": row[2],
                "failed_steps": row[3] or 0,
                "total_duration_ms": round(row[4] or 0, 2),
                "status": "failed" if (row[3] or 0) > 0 else "success",
            }
            for row in rows
        ]


# Alias for backward compatibility
TraceDatabase = GenericTraceDatabase
