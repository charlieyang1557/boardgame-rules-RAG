
from retrieval.reranker import RerankResult, Reranker


class TestReranker:
    def setup_method(self) -> None:
        self.reranker = Reranker()

    def test_returns_correct_type(self) -> None:
        chunks = [{"chunk_id": "c1", "text": "The player takes gems from the supply."}]
        results = self.reranker.rerank("How do I take gems?", chunks)
        assert len(results) == 1
        assert isinstance(results[0], RerankResult)

    def test_sigmoid_scores_in_range(self) -> None:
        chunks = [
            {"chunk_id": "c1", "text": "Splendor is a game about collecting gems."},
            {"chunk_id": "c2", "text": "Weather forecast for tomorrow is sunny."},
        ]
        results = self.reranker.rerank("How do I collect gems in Splendor?", chunks)
        for r in results:
            assert 0.0 < r.sigmoid_score < 1.0

    def test_sorted_descending(self) -> None:
        chunks = [
            {"chunk_id": "c1", "text": "The weather is nice today."},
            {"chunk_id": "c2", "text": "Players take turns collecting gem tokens."},
            {"chunk_id": "c3", "text": "Noble tiles visit players with enough prestige."},
        ]
        results = self.reranker.rerank("How do nobles work in Splendor?", chunks, top_k=3)
        for i in range(len(results) - 1):
            assert results[i].sigmoid_score >= results[i + 1].sigmoid_score

    def test_top_k_limits_output(self) -> None:
        chunks = [{"chunk_id": f"c{i}", "text": f"Text chunk {i}"} for i in range(10)]
        results = self.reranker.rerank("query", chunks, top_k=3)
        assert len(results) == 3

    def test_empty_chunks(self) -> None:
        results = self.reranker.rerank("query", [])
        assert results == []

    def test_dual_query_takes_max_score(self) -> None:
        chunks = [
            {"chunk_id": "c1", "text": "[Splendor - Gems] A player may take 2 gem tokens of the same color if at least 4 tokens of that color are available."},
        ]
        # Score with a weak query
        weak = self.reranker.rerank("something unrelated about weather", chunks, top_k=1)
        # Score with dual query where alt_query is strong
        dual = self.reranker.rerank(
            "something unrelated about weather", chunks, top_k=1,
            alt_query="Can I take 2 gems of the same color?",
        )
        # Dual should be >= weak because it takes max
        assert dual[0].sigmoid_score >= weak[0].sigmoid_score

    def test_dual_query_same_as_single_when_identical(self) -> None:
        chunks = [{"chunk_id": "c1", "text": "Splendor is about collecting gems."}]
        q = "How do I collect gems?"
        single = self.reranker.rerank(q, chunks, top_k=1)
        dual = self.reranker.rerank(q, chunks, top_k=1, alt_query=q)
        assert abs(single[0].sigmoid_score - dual[0].sigmoid_score) < 1e-6

    def test_dual_query_none_alt_same_as_single(self) -> None:
        chunks = [{"chunk_id": "c1", "text": "Splendor is about collecting gems."}]
        q = "How do I collect gems?"
        single = self.reranker.rerank(q, chunks, top_k=1)
        dual = self.reranker.rerank(q, chunks, top_k=1, alt_query=None)
        assert abs(single[0].sigmoid_score - dual[0].sigmoid_score) < 1e-6

    def test_relevant_chunk_scores_higher(self) -> None:
        chunks = [
            {"chunk_id": "relevant", "text": "[Splendor - Gems] A player may take 2 gem tokens of the same color if at least 4 tokens of that color are available."},
            {"chunk_id": "irrelevant", "text": "The capital of France is Paris. It has many famous landmarks."},
        ]
        results = self.reranker.rerank("Can I take 2 gems of the same color?", chunks, top_k=2)
        assert results[0].chunk_id == "relevant"
