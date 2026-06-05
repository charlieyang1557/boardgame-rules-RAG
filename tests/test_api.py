"""Tests for API endpoints — health and feedback only (no live pipeline)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from api.feedback import set_logger
from query_logging.query_logger import QueryLogger


@pytest.fixture
def logger(tmp_path) -> QueryLogger:
    db_path = os.path.join(str(tmp_path), "test.db")
    return QueryLogger(db_path=db_path)


@pytest.fixture
def client(logger: QueryLogger) -> TestClient:
    """Create test client with feedback logger injected."""
    from api.main import app

    set_logger(logger)
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "games_loaded" in data
        assert isinstance(data["games_loaded"], list)


class TestFeedbackEndpoint:
    def test_submit_feedback(self, client: TestClient, logger: QueryLogger) -> None:
        # First create a query log entry to reference
        qid = logger.log_query("s1", "q", "q", "splendor", 1, [], "a", 1.0, False)
        response = client.post(
            "/api/feedback",
            json={"session_id": "s1", "query_id": qid, "helpful": True, "comment": "good"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_feedback_stored_in_db(self, client: TestClient, logger: QueryLogger) -> None:
        qid = logger.log_query("s1", "q", "q", "splendor", 1, [], "a", 1.0, False)
        client.post(
            "/api/feedback",
            json={"session_id": "s1", "query_id": qid, "helpful": False, "comment": "wrong"},
        )
        feedback = logger.get_feedback(qid)
        assert len(feedback) == 1
        assert feedback[0]["helpful"] == 0
        assert feedback[0]["comment"] == "wrong"

    def test_feedback_missing_fields(self, client: TestClient) -> None:
        response = client.post("/api/feedback", json={"session_id": "s1"})
        assert response.status_code == 422  # Validation error


class TestAskRequestLanguage:
    def test_language_defaults_to_en(self) -> None:
        from api.main import AskRequest

        req = AskRequest(query="How do sailors win?", game_name="ftk")
        assert req.language == "en"

    def test_language_accepts_zh(self) -> None:
        from api.main import AskRequest

        req = AskRequest(query="水手如何獲勝？", game_name="ftk", language="zh")
        assert req.language == "zh"

    def test_invalid_language_falls_back_to_en(self) -> None:
        from api.main import AskRequest

        req = AskRequest(query="q", game_name="ftk", language="fr")
        assert req.language == "en"
