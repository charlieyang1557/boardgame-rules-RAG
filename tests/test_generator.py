from generation.generator import generate_tier3


class TestGenerateTier3:
    def test_output_has_tier3(self) -> None:
        result = generate_tier3([{"chunk_id": "c1", "text": "Rule text", "score": 0.9}])
        assert result.tier == 3

    def test_output_contains_directness_label(self) -> None:
        result = generate_tier3([{"chunk_id": "c1", "text": "Rule text", "score": 0.9}])
        assert "does not address this directly" in result.answer

    def test_output_contains_chunk_ids(self) -> None:
        chunks = [
            {"chunk_id": "c1", "text": "First rule", "score": 0.9},
            {"chunk_id": "c2", "text": "Second rule", "score": 0.8},
        ]
        result = generate_tier3(chunks)
        assert "c1" in result.answer
        assert "c2" in result.answer

    def test_empty_chunks_input_works(self) -> None:
        result = generate_tier3([])
        assert result.tier == 3
        assert "Closest relevant rules found" in result.answer

    def test_citations_list_is_empty(self) -> None:
        result = generate_tier3([{"chunk_id": "c1", "text": "Rule text", "score": 0.9}])
        assert result.citations == []

    def test_default_language_uses_english_labels(self) -> None:
        result = generate_tier3([{"chunk_id": "c1", "text": "Rule text", "score": 0.9}])
        assert "does not address this directly" in result.answer

    def test_chinese_language_localizes_boilerplate(self) -> None:
        result = generate_tier3(
            [{"chunk_id": "c1", "text": "Rule text", "score": 0.9}], language="zh"
        )
        # Boilerplate labels are localized; English template is gone.
        assert "规则书没有直接说明" in result.answer
        assert "does not address this directly" not in result.answer
        # Verbatim official chunk excerpt stays in English.
        assert "Rule text" in result.answer
        assert result.tier == 3

    def test_chinese_with_no_client_makes_no_api_call(self) -> None:
        # Without an anthropic client there is no interpretation call; labels only.
        result = generate_tier3(
            [{"chunk_id": "c1", "text": "Rule text", "score": 0.9}],
            anthropic_client=None, query="anything", language="zh",
        )
        assert result.tier == 3
