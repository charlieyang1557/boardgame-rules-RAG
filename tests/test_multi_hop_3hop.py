"""Tests for 3-hop Chain-of-Retrieval support."""
from unittest.mock import MagicMock

from retrieval.multi_hop import ChainOfRetrieval


class TestThreeHopChain:
    def _make_chain(self, max_hops: int = 3) -> ChainOfRetrieval:
        return ChainOfRetrieval(
            searcher=MagicMock(),
            reranker=MagicMock(),
            anthropic_client=MagicMock(),
            openai_client=MagicMock(),
            max_hops=max_hops,
        )

    def test_max_hops_3_is_accepted(self) -> None:
        chain = self._make_chain(max_hops=3)
        assert chain.max_hops == 3

    def test_early_termination_at_hop1(self) -> None:
        """If answerable at hop 1, should return hops_used=1."""
        chain = self._make_chain(max_hops=3)
        mock_chunks = [{"chunk_id": "c1", "text": "answer text", "sigmoid_score": 0.9}]
        chain._search_and_rerank = MagicMock(return_value=mock_chunks)
        chain._embed = MagicMock(return_value=[0.1] * 3072)

        answerable_response = (
            "ANSWERABLE: yes\n"
            "ANSWER: The answer is 42 [c1]\n"
            "MISSING: \n"
            "FOLLOW_UP_QUERY: "
        )
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=answerable_response)]
        chain.anthropic_client.messages.create.return_value = mock_message

        config = MagicMock()
        config.rerank_top_k = 8
        config.rrf_k = 60
        config.hybrid_top_k = 40

        result = chain.retrieve_and_reason("test query", "fcm", config)
        assert result.hops_used == 1
        assert result.is_answerable is True

    def test_three_hops_when_needed(self) -> None:
        """If not answerable at hop 1 or 2, should proceed to hop 3."""
        chain = self._make_chain(max_hops=3)
        hop_chunks = [
            [{"chunk_id": "c1", "text": "dinnertime pricing", "sigmoid_score": 0.5}],
            [{"chunk_id": "c2", "text": "milestone bonus", "sigmoid_score": 0.4}],
            [{"chunk_id": "c3", "text": "garden rules", "sigmoid_score": 0.3}],
        ]
        call_count = {"n": 0}

        def mock_search(*a, **kw):
            idx = call_count["n"]
            call_count["n"] += 1
            return hop_chunks[idx]

        chain._search_and_rerank = MagicMock(side_effect=mock_search)
        chain._embed = MagicMock(return_value=[0.1] * 3072)

        responses = [
            "ANSWERABLE: no\nANSWER: \nMISSING: milestone bonus info\nFOLLOW_UP_QUERY: FCM milestone first burger marketed bonus",
            "ANSWERABLE: no\nANSWER: \nMISSING: garden doubling rules\nFOLLOW_UP_QUERY: FCM garden doubles unit price",
            "ANSWERABLE: yes\nANSWER: Total income is $125 [c1][c2][c3]\nMISSING: \nFOLLOW_UP_QUERY: ",
        ]
        resp_idx = {"i": 0}

        def mock_create(**kwargs):
            msg = MagicMock()
            msg.content = [MagicMock(text=responses[resp_idx["i"]])]
            resp_idx["i"] += 1
            return msg

        chain.anthropic_client.messages.create.side_effect = mock_create

        config = MagicMock()
        config.rerank_top_k = 8
        config.rrf_k = 60
        config.hybrid_top_k = 40

        result = chain.retrieve_and_reason("income query", "fcm", config)
        assert result.hops_used == 3
        assert result.is_answerable is True
        chunk_ids = {c["chunk_id"] for c in result.merged_chunks}
        assert chunk_ids == {"c1", "c2", "c3"}

    def test_no_follow_up_query_stops_early(self) -> None:
        """If not answerable but no follow-up query, generate best-effort."""
        chain = self._make_chain(max_hops=3)
        mock_chunks = [{"chunk_id": "c1", "text": "some text", "sigmoid_score": 0.5}]
        chain._search_and_rerank = MagicMock(return_value=mock_chunks)
        chain._embed = MagicMock(return_value=[0.1] * 3072)

        response = "ANSWERABLE: no\nANSWER: \nMISSING: something\nFOLLOW_UP_QUERY: "
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response)]
        chain.anthropic_client.messages.create.return_value = mock_message
        chain._generate_final = MagicMock(return_value="best effort answer")

        config = MagicMock()
        config.rerank_top_k = 8
        config.rrf_k = 60
        config.hybrid_top_k = 40

        result = chain.retrieve_and_reason("test", "fcm", config)
        assert result.hops_used == 1
        assert result.is_answerable is True
