from retrieval.hybrid_search import SearchResult, rrf_fuse


class TestRRFFuse:
    def test_basic_fusion(self) -> None:
        dense = [
            SearchResult(chunk_id="a", text="text_a", score=0.9, source="dense"),
            SearchResult(chunk_id="b", text="text_b", score=0.8, source="dense"),
        ]
        sparse = [
            SearchResult(chunk_id="b", text="text_b", score=5.0, source="sparse"),
            SearchResult(chunk_id="c", text="text_c", score=3.0, source="sparse"),
        ]
        results = rrf_fuse(dense, sparse, k=60, top_k=10)

        ids = [r.chunk_id for r in results]
        # "b" appears in both lists, should rank higher
        assert ids[0] == "b"
        assert set(ids) == {"a", "b", "c"}

    def test_all_results_are_fused_source(self) -> None:
        dense = [SearchResult("a", "t", 0.9, "dense")]
        sparse = [SearchResult("b", "t", 1.0, "sparse")]
        results = rrf_fuse(dense, sparse, k=60, top_k=10)
        assert all(r.source == "fused" for r in results)

    def test_top_k_limit(self) -> None:
        dense = [SearchResult(f"d{i}", f"t{i}", 1.0 - i * 0.01, "dense") for i in range(20)]
        sparse = [SearchResult(f"s{i}", f"t{i}", 5.0 - i * 0.1, "sparse") for i in range(20)]
        results = rrf_fuse(dense, sparse, k=60, top_k=5)
        assert len(results) == 5

    def test_empty_inputs(self) -> None:
        results = rrf_fuse([], [], k=60, top_k=10)
        assert results == []

    def test_one_source_empty(self) -> None:
        dense = [SearchResult("a", "t", 0.9, "dense")]
        results = rrf_fuse(dense, [], k=60, top_k=10)
        assert len(results) == 1
        assert results[0].chunk_id == "a"

    def test_scores_are_positive(self) -> None:
        dense = [SearchResult("a", "t", 0.9, "dense")]
        sparse = [SearchResult("a", "t", 5.0, "sparse")]
        results = rrf_fuse(dense, sparse, k=60, top_k=10)
        assert all(r.score > 0 for r in results)

    def test_duplicate_chunk_gets_higher_score(self) -> None:
        dense = [
            SearchResult("a", "t", 0.9, "dense"),
            SearchResult("b", "t", 0.8, "dense"),
        ]
        sparse = [
            SearchResult("a", "t", 5.0, "sparse"),
            SearchResult("c", "t", 4.0, "sparse"),
        ]
        results = rrf_fuse(dense, sparse, k=60, top_k=10)
        # "a" appears in both, should have highest score
        scores_by_id = {r.chunk_id: r.score for r in results}
        assert scores_by_id["a"] > scores_by_id["b"]
        assert scores_by_id["a"] > scores_by_id["c"]

    def test_rrf_k_affects_scoring(self) -> None:
        dense = [SearchResult("a", "t", 0.9, "dense")]
        sparse = [SearchResult("a", "t", 5.0, "sparse")]
        result_k10 = rrf_fuse(dense, sparse, k=10, top_k=1)
        result_k100 = rrf_fuse(dense, sparse, k=100, top_k=1)
        # Lower k means each rank contributes more weight
        assert result_k10[0].score > result_k100[0].score
