from retrieval.multi_hop import _parse_answerable_response, _format_chunks


class TestParseAnswerableResponse:
    def test_answerable_yes(self) -> None:
        text = "ANSWERABLE: yes\nANSWER: The rule says X [chunk1]."
        is_ans, answer, missing, follow_up = _parse_answerable_response(text)
        assert is_ans is True
        assert "rule says X" in answer
        assert follow_up == ""

    def test_answerable_no(self) -> None:
        text = (
            "ANSWERABLE: no\n"
            "MISSING: Need information about Cop effects\n"
            "FOLLOW_UP_QUERY: Speakeasy Cop Operating building rules"
        )
        is_ans, answer, missing, follow_up = _parse_answerable_response(text)
        assert is_ans is False
        assert "Cop effects" in missing
        assert "Cop Operating" in follow_up

    def test_case_insensitive(self) -> None:
        text = "answerable: YES\nanswer: The answer is here [c1]."
        is_ans, answer, _, _ = _parse_answerable_response(text)
        assert is_ans is True

    def test_empty_response(self) -> None:
        is_ans, answer, missing, follow_up = _parse_answerable_response("")
        assert is_ans is False
        assert answer == ""


class TestFormatChunks:
    def test_single_chunk(self) -> None:
        chunks = [{"chunk_id": "c1", "text": "Some rule text."}]
        result = _format_chunks(chunks)
        assert "[c1]: Some rule text." in result

    def test_multiple_chunks(self) -> None:
        chunks = [
            {"chunk_id": "c1", "text": "Rule 1."},
            {"chunk_id": "c2", "text": "Rule 2."},
        ]
        result = _format_chunks(chunks)
        assert "[c1]: Rule 1." in result
        assert "[c2]: Rule 2." in result
