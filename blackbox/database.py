import json
import sqlite3
from typing import List

from .models import TraceEvent


class TraceDatabase:
    """
    SQLite storage for Black Box execution traces.
    """

    def __init__(self, db_path: str = "blackbox.db"):
        self.db_path = db_path
        self._create_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trace_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                name TEXT NOT NULL,
                inputs TEXT,
                outputs TEXT,
                state_before TEXT,
                state_after TEXT,
                status TEXT NOT NULL,
                duration_ms REAL,
                error TEXT,
                metadata TEXT
            )
            """
        )

        connection.commit()
        connection.close()

    def save_event(self, event: TraceEvent):
        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO trace_events (
                trace_id,
                step_id,
                timestamp,
                event_type,
                name,
                inputs,
                outputs,
                state_before,
                state_after,
                status,
                duration_ms,
                error,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.trace_id,
                event.step_id,
                event.timestamp.isoformat(),
                event.event_type,
                event.name,
                json.dumps(event.inputs),
                json.dumps(event.outputs),
                json.dumps(event.state_before),
                json.dumps(event.state_after),
                event.status,
                event.duration_ms,
                event.error,
                json.dumps(event.metadata),
            ),
        )

        connection.commit()
        connection.close()

    def get_trace(self, trace_id: str) -> List[dict]:
        connection = self._connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                trace_id,
                step_id,
                timestamp,
                event_type,
                name,
                inputs,
                outputs,
                state_before,
                state_after,
                status,
                duration_ms,
                error,
                metadata
            FROM trace_events
            WHERE trace_id = ?
            ORDER BY id ASC
            """,
            (trace_id,),
        )

        rows = cursor.fetchall()

        connection.close()

        events = []

        for row in rows:
            events.append(
                {
                    "trace_id": row[0],
                    "step_id": row[1],
                    "timestamp": row[2],
                    "event_type": row[3],
                    "name": row[4],
                    "inputs": json.loads(row[5]),
                    "outputs": json.loads(row[6]),
                    "state_before": json.loads(row[7]),
                    "state_after": json.loads(row[8]),
                    "status": row[9],
                    "duration_ms": row[10],
                    "error": row[11],
                    "metadata": json.loads(row[12]),
                }
            )

        return events
