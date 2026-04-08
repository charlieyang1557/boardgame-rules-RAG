from conversation.session_manager import SessionManager


def test_add_turn_stores_turns() -> None:
    manager = SessionManager()

    manager.add_turn("session-1", "How do turns work?", "Take one action.")

    history = manager.get_history("session-1")
    assert len(history) == 1
    assert history[0].query == "How do turns work?"
    assert history[0].answer == "Take one action."


def test_max_three_turns_enforced() -> None:
    manager = SessionManager(max_turns=3)

    manager.add_turn("session-1", "q1", "a1")
    manager.add_turn("session-1", "q2", "a2")
    manager.add_turn("session-1", "q3", "a3")
    manager.add_turn("session-1", "q4", "a4")

    history = manager.get_history("session-1")
    assert [turn.query for turn in history] == ["q2", "q3", "q4"]


def test_get_history_returns_empty_list_for_unknown_session() -> None:
    manager = SessionManager()

    assert manager.get_history("missing") == []


def test_get_history_text_returns_empty_string_for_no_history() -> None:
    manager = SessionManager()

    assert manager.get_history_text("missing") == ""


def test_get_history_text_truncates_to_max_tokens() -> None:
    manager = SessionManager(max_turns=3, max_tokens=2000)
    long_answer = "token " * 2500

    manager.add_turn("session-1", "short", "brief")
    manager.add_turn("session-1", "long", long_answer)

    history_text = manager.get_history_text("session-1")
    assert history_text == ""


def test_clear_session_removes_session() -> None:
    manager = SessionManager()
    manager.add_turn("session-1", "q1", "a1")

    manager.clear_session("session-1")

    assert manager.get_history("session-1") == []


def test_multiple_sessions_are_independent() -> None:
    manager = SessionManager()
    manager.add_turn("session-1", "q1", "a1")
    manager.add_turn("session-2", "q2", "a2")

    history_one = manager.get_history("session-1")
    history_two = manager.get_history("session-2")

    assert len(history_one) == 1
    assert history_one[0].query == "q1"
    assert len(history_two) == 1
    assert history_two[0].query == "q2"


def test_get_history_text_drops_oldest_turn_first_when_over_budget() -> None:
    manager = SessionManager(max_turns=3, max_tokens=7)

    manager.add_turn("session-1", "first", "first")
    manager.add_turn("session-1", "second", "second")
    manager.add_turn("session-1", "third", "third")

    history_text = manager.get_history_text("session-1")

    assert history_text == "User: third\nAssistant: third"
    assert "User: second" not in history_text
    assert "User: first" not in history_text
