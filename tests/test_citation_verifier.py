from verification.citation_verifier import compute_token_overlap, verify_citations


class TestComputeTokenOverlap:
    def test_full_overlap_is_one(self) -> None:
        assert compute_token_overlap("take two gems", "take two gems") == 1.0

    def test_no_overlap_is_zero(self) -> None:
        assert compute_token_overlap("take two gems", "reserve a card") == 0.0

    def test_partial_overlap(self) -> None:
        overlap = compute_token_overlap("take two gems", "take one token")
        assert overlap == 1 / 3


class TestVerifyCitations:
    def test_high_overlap_marks_all_supported(self) -> None:
        answer = "Players may take two gems on their turn [c1]"
        chunks = [{"chunk_id": "c1", "text": "Players may take two gems on their turn."}]
        result = verify_citations(answer, chunks)
        assert result.all_supported is True
        assert len(result.details) == 1
        assert result.details[0].supported is True

    def test_missing_chunk_id_is_unsupported(self) -> None:
        answer = "Players may take two gems on their turn [missing]"
        chunks = [{"chunk_id": "c1", "text": "Players may take gems."}]
        result = verify_citations(answer, chunks)
        assert result.all_supported is False
        assert len(result.details) == 1
        assert result.details[0].supported is False

    def test_short_fragments_filtered_out(self) -> None:
        answer = "Additionally, [c1] the rules are clear [c1]"
        chunks = [{"chunk_id": "c1", "text": "The rules are clear about gem tokens."}]
        result = verify_citations(answer, chunks)
        # "Additionally," is < 4 words, should be filtered
        # "the rules are clear" is 4 words, should be kept
        assert len(result.details) == 1
        assert result.details[0].supported is True

    def test_empty_answer_has_no_claims(self) -> None:
        result = verify_citations("", [{"chunk_id": "c1", "text": "Players may take gems."}])
        assert result.all_supported is True
        assert result.details == []
