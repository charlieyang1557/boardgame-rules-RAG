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
