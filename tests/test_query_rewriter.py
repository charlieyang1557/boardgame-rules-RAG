from types import SimpleNamespace
from unittest.mock import MagicMock

from retrieval.query_rewriter import RewriteResult, rewrite_query


def test_rewrite_query_calls_client_with_haiku_model() -> None:
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="GAME: splendor\nQUERY: revised query")]
    )

    rewrite_query("raw query", "", client)

    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-haiku-4-5-20251001"
    assert kwargs["max_tokens"] == 256


def test_rewrite_query_parses_game_and_query() -> None:
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="GAME: catan\nQUERY: longest road rules")]
    )

    result = rewrite_query("what about that road thing", "", client)

    assert result == RewriteResult(
        rewritten_query="longest road rules",
        game_name="catan",
    )


def test_rewrite_query_falls_back_to_default_game_on_api_error() -> None:
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api failure")

    result = rewrite_query("raw query", "", client, default_game="azul")

    assert result.game_name == "azul"


def test_rewrite_query_falls_back_to_raw_query_on_api_error() -> None:
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api failure")

    result = rewrite_query("raw query", "", client)

    assert result.rewritten_query == "raw query"


def test_rewrite_query_includes_history_in_prompt_when_provided() -> None:
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="GAME: splendor\nQUERY: revised query")]
    )
    history = "User: Can I reserve?\nAssistant: Yes."

    rewrite_query("What about that?", history, client)

    _, kwargs = client.messages.create.call_args
    prompt = kwargs["messages"][0]["content"]
    assert history in prompt
    assert "What about that?" in prompt
