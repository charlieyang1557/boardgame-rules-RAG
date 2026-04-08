
from cache.semantic_cache import SemanticCache, _cosine_similarity


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-9

    def test_opposite_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) - (-1.0)) < 1e-9

    def test_zero_vector(self) -> None:
        a = [0.0, 0.0]
        b = [1.0, 2.0]
        assert _cosine_similarity(a, b) == 0.0


class TestSemanticCache:
    def test_empty_cache_returns_none(self) -> None:
        cache = SemanticCache()
        assert cache.lookup([1.0, 2.0, 3.0]) is None

    def test_exact_match_returns_cached(self) -> None:
        cache = SemanticCache(threshold=0.92)
        emb = [1.0, 0.0, 0.0]
        response = {"answer": "test", "tier": 1}
        cache.store(emb, response, tier=1)
        result = cache.lookup(emb)
        assert result == response

    def test_below_threshold_returns_none(self) -> None:
        cache = SemanticCache(threshold=0.92)
        cache.store([1.0, 0.0, 0.0], {"answer": "test"}, tier=1)
        # Orthogonal vector — cosine sim = 0
        result = cache.lookup([0.0, 1.0, 0.0])
        assert result is None

    def test_tier3_not_cached(self) -> None:
        cache = SemanticCache()
        emb = [1.0, 0.0, 0.0]
        cache.store(emb, {"answer": "tier3 answer"}, tier=3)
        assert cache.size == 0
        assert cache.lookup(emb) is None

    def test_tier1_cached(self) -> None:
        cache = SemanticCache()
        cache.store([1.0, 0.0], {"answer": "a"}, tier=1)
        assert cache.size == 1

    def test_similar_but_not_identical(self) -> None:
        cache = SemanticCache(threshold=0.92)
        cache.store([1.0, 0.0, 0.0], {"answer": "cached"}, tier=1)
        # Very similar vector (small perturbation)
        similar = [0.99, 0.01, 0.0]
        result = cache.lookup(similar)
        assert result is not None
        assert result["answer"] == "cached"

    def test_multiple_entries_best_match(self) -> None:
        cache = SemanticCache(threshold=0.92)
        cache.store([1.0, 0.0, 0.0], {"answer": "first"}, tier=1)
        cache.store([0.0, 1.0, 0.0], {"answer": "second"}, tier=1)
        # Query close to first entry
        result = cache.lookup([0.99, 0.01, 0.0])
        assert result is not None
        assert result["answer"] == "first"

    def test_clear(self) -> None:
        cache = SemanticCache()
        cache.store([1.0], {"answer": "a"}, tier=1)
        cache.store([0.0], {"answer": "b"}, tier=1)
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0
        assert cache.lookup([1.0]) is None

    def test_threshold_boundary(self) -> None:
        cache = SemanticCache(threshold=0.99)
        cache.store([1.0, 0.0], {"answer": "strict"}, tier=1)
        # cos(1.0, 0.0) and (0.95, 0.31) ≈ 0.95 < 0.99
        result = cache.lookup([0.95, 0.31])
        assert result is None
