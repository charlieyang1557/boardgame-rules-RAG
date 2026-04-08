from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone


class QueryLogger:
    def __init__(self, db_path: str = "logs/query_log.db") -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_tables(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    raw_query TEXT NOT NULL,
                    rewritten_query TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    tier_decision INTEGER NOT NULL,
                    top_chunks TEXT NOT NULL,
                    final_answer TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    cache_hit INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    query_id INTEGER NOT NULL,
                    helpful INTEGER NOT NULL,
                    comment TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (query_id) REFERENCES query_logs(id)
                )
            """)

    def log_query(
        self,
        session_id: str,
        raw_query: str,
        rewritten_query: str,
        game_name: str,
        tier_decision: int,
        top_chunks: list[dict],
        final_answer: str,
        latency_ms: float,
        cache_hit: bool,
    ) -> int:
        timestamp = datetime.now(timezone.utc).isoformat()
        truncated_answer = final_answer[:500]
        chunks_json = json.dumps(top_chunks)
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO query_logs
                    (timestamp, session_id, raw_query, rewritten_query, game_name,
                     tier_decision, top_chunks, final_answer, latency_ms, cache_hit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    session_id,
                    raw_query,
                    rewritten_query,
                    game_name,
                    tier_decision,
                    chunks_json,
                    truncated_answer,
                    latency_ms,
                    int(cache_hit),
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def log_feedback(
        self,
        session_id: str,
        query_id: int,
        helpful: bool,
        comment: str = "",
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO feedback (timestamp, session_id, query_id, helpful, comment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, session_id, query_id, int(helpful), comment),
            )

    def get_query(self, query_id: int) -> dict | None:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM query_logs WHERE id = ?", (query_id,)).fetchone()
            return dict(row) if row else None

    def get_feedback(self, query_id: int) -> list[dict]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM feedback WHERE query_id = ?", (query_id,)).fetchall()
            return [dict(row) for row in rows]
