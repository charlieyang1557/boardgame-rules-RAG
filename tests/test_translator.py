from types import SimpleNamespace
from unittest.mock import MagicMock

from generation.translator import translate_answer


def _client_returning(text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=text)]
    )
    return client


def test_english_is_passthrough_without_api_call() -> None:
    client = MagicMock()
    out = translate_answer("Sailors win at Bluewater Bay [ftk_p8_c6].", "en", client)
    assert out == "Sailors win at Bluewater Bay [ftk_p8_c6]."
    client.messages.create.assert_not_called()


def test_empty_answer_is_passthrough_without_api_call() -> None:
    client = MagicMock()
    assert translate_answer("", "zh", client) == ""
    assert translate_answer("   ", "zh", client) == "   "
    client.messages.create.assert_not_called()


def test_zh_calls_haiku_and_returns_translated_text() -> None:
    client = _client_returning("水手在藍水灣獲勝 [ftk_p8_c6]。")
    out = translate_answer("Sailors win at Bluewater Bay [ftk_p8_c6].", "zh", client)
    assert out == "水手在藍水灣獲勝 [ftk_p8_c6]。"
    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-haiku-4-5-20251001"
    assert kwargs["temperature"] == 0


def test_zh_prompt_instructs_marker_preservation_and_includes_answer() -> None:
    client = _client_returning("翻譯結果")
    answer = "Each player starts with 3 guns [ftk_p4_c2]."
    translate_answer(answer, "zh", client)
    _, kwargs = client.messages.create.call_args
    system = kwargs["system"].lower()
    assert "[" in kwargs["system"] and "marker" in system or "citation" in system
    # the answer to translate is passed to the model
    user_content = kwargs["messages"][0]["content"]
    assert answer in user_content


def test_translation_failure_falls_back_to_english() -> None:
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("api down")
    answer = "Pirates win at Crimson Cove [ftk_p8_c6]."
    assert translate_answer(answer, "zh", client) == answer


def test_empty_model_response_falls_back_to_english() -> None:
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(content=[])
    answer = "Cult wins in the north [ftk_p8_c6]."
    assert translate_answer(answer, "zh", client) == answer
