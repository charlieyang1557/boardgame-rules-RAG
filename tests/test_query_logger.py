import json
import os

import pytest

from query_logging.query_logger import QueryLogger


@pytest.fixture
def logger(tmp_path: object) -> QueryLogger:
    db_path = os.path.join(str(tmp_path), "test_query_log.db")
    return QueryLogger(db_path=db_path)


class TestQueryLoggerInit:
    def test_creates_db_file(self, logger: QueryLogger) -> None:
        assert os.path.exists(logger.db_path)

    def test_creates_tables(self, logger: QueryLogger) -> None:
        import sqlite3

        conn = sqlite3.connect(logger.db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert "query_logs" in table_names
        assert "feedback" in table_names
        conn.close()


class TestLogQuery:
    def test_returns_query_id(self, logger: QueryLogger) -> None:
        qid = logger.log_query(
            session_id="sess1",
            raw_query="How many gems can I take?",
            rewritten_query="How many gem tokens can a player take on their turn?",
            game_name="splendor",
            tier_decision=1,
            top_chunks=[{"chunk_id": "c1", "score": 0.9, "text": "sample"}],
            final_answer="You can take up to 3 gems of different colors.",
            latency_ms=150.5,
            cache_hit=False,
        )
        assert isinstance(qid, int)
        assert qid > 0

    def test_stores_all_fields(self, logger: QueryLogger) -> None:
        qid = logger.log_query(
            session_id="sess2",
            raw_query="raw",
            rewritten_query="rewritten",
            game_name="splendor",
            tier_decision=3,
            top_chunks=[{"id": "c1"}],
            final_answer="answer",
            latency_ms=42.0,
            cache_hit=True,
        )
        row = logger.get_query(qid)
        assert row is not None
        assert row["session_id"] == "sess2"
        assert row["raw_query"] == "raw"
        assert row["rewritten_query"] == "rewritten"
        assert row["game_name"] == "splendor"
        assert row["tier_decision"] == 3
        assert json.loads(row["top_chunks"]) == [{"id": "c1"}]
        assert row["final_answer"] == "answer"
        assert row["latency_ms"] == 42.0
        assert row["cache_hit"] == 1

    def test_truncates_long_answer(self, logger: QueryLogger) -> None:
        long_answer = "x" * 1000
        qid = logger.log_query(
            session_id="sess3",
            raw_query="q",
            rewritten_query="q",
            game_name="splendor",
            tier_decision=1,
            top_chunks=[],
            final_answer=long_answer,
            latency_ms=10.0,
            cache_hit=False,
        )
        row = logger.get_query(qid)
        assert row is not None
        assert len(row["final_answer"]) == 500

    def test_timestamp_is_iso_format(self, logger: QueryLogger) -> None:
        qid = logger.log_query(
            session_id="sess4",
            raw_query="q",
            rewritten_query="q",
            game_name="splendor",
            tier_decision=1,
            top_chunks=[],
            final_answer="a",
            latency_ms=1.0,
            cache_hit=False,
        )
        row = logger.get_query(qid)
        assert row is not None
        assert "T" in row["timestamp"]
        assert "+" in row["timestamp"] or "Z" in row["timestamp"]

    def test_incremental_ids(self, logger: QueryLogger) -> None:
        qid1 = logger.log_query("s", "q", "q", "splendor", 1, [], "a", 1.0, False)
        qid2 = logger.log_query("s", "q", "q", "splendor", 1, [], "a", 1.0, False)
        assert qid2 == qid1 + 1


class TestLogFeedback:
    def test_stores_feedback(self, logger: QueryLogger) -> None:
        qid = logger.log_query("s", "q", "q", "splendor", 1, [], "a", 1.0, False)
        logger.log_feedback(session_id="s", query_id=qid, helpful=True, comment="great")
        feedback = logger.get_feedback(qid)
        assert len(feedback) == 1
        assert feedback[0]["helpful"] == 1
        assert feedback[0]["comment"] == "great"

    def test_multiple_feedback_per_query(self, logger: QueryLogger) -> None:
        qid = logger.log_query("s", "q", "q", "splendor", 1, [], "a", 1.0, False)
        logger.log_feedback("s", qid, True, "good")
        logger.log_feedback("s", qid, False, "bad")
        feedback = logger.get_feedback(qid)
        assert len(feedback) == 2

    def test_empty_comment_default(self, logger: QueryLogger) -> None:
        qid = logger.log_query("s", "q", "q", "splendor", 1, [], "a", 1.0, False)
        logger.log_feedback("s", qid, False)
        feedback = logger.get_feedback(qid)
        assert feedback[0]["comment"] == ""


    def test_feedback_rejects_nonexistent_query(self, logger: QueryLogger) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            logger.log_feedback("s", 999, True, "bad")

    def test_feedback_rejects_wrong_session(self, logger: QueryLogger) -> None:
        qid = logger.log_query("session_a", "q", "q", "splendor", 1, [], "a", 1.0, False)
        with pytest.raises(ValueError, match="does not belong to session"):
            logger.log_feedback("session_b", qid, True, "wrong session")


class TestGetQuery:
    def test_nonexistent_returns_none(self, logger: QueryLogger) -> None:
        assert logger.get_query(999) is None
