"""Cross-game isolation tests.

These tests verify that the multi-game pipeline retrieves chunks from
the correct game namespace and that the semantic cache is partitioned.
They require API keys and ingested data to run.
"""
from __future__ import annotations

import pytest

from cache.semantic_cache import SemanticCache


class TestSemanticCacheIsolation:
    """Cache must never serve a hit from the wrong game."""

    def test_cache_miss_wrong_game(self) -> None:
        cache = SemanticCache(threshold=0.92)
        emb = [1.0, 0.0, 0.0]
        cache.store(emb, {"answer": "splendor answer", "tier": 1}, tier=1, game_name="splendor")
        assert cache.lookup(emb, game_name="catan") is None

    def test_cache_hit_correct_game(self) -> None:
        cache = SemanticCache(threshold=0.92)
        emb = [1.0, 0.0, 0.0]
        cache.store(emb, {"answer": "catan answer", "tier": 1}, tier=1, game_name="catan")
        result = cache.lookup(emb, game_name="catan")
        assert result is not None
        assert result["answer"] == "catan answer"

    def test_same_query_different_games_different_answers(self) -> None:
        cache = SemanticCache(threshold=0.92)
        emb = [1.0, 0.0, 0.0]
        cache.store(emb, {"answer": "splendor: 3 gems", "tier": 1}, tier=1, game_name="splendor")
        cache.store(emb, {"answer": "catan: 1 resource", "tier": 1}, tier=1, game_name="catan")
        assert cache.lookup(emb, game_name="splendor")["answer"] == "splendor: 3 gems"
        assert cache.lookup(emb, game_name="catan")["answer"] == "catan: 1 resource"


class TestGameConfigValidation:
    """API must reject unknown games."""

    def test_unknown_game_in_config(self) -> None:
        from routing.game_config import GAME_CONFIG

        assert "splendor" in GAME_CONFIG
        assert "catan" in GAME_CONFIG
        assert "monopoly" not in GAME_CONFIG

    def test_get_config_unknown_raises(self) -> None:
        from routing.game_config import get_config

        with pytest.raises(ValueError, match="Unknown game"):
            get_config("monopoly")


class TestPerGameSearcher:
    """Per-game searcher must load correct BM25 index."""

    def test_splendor_searcher_has_splendor_chunks(self) -> None:
        from api.main import _get_searcher

        searcher = _get_searcher("splendor")
        if searcher is None:
            pytest.skip("Splendor BM25 not ingested")
        assert all("splendor" in cid for cid in searcher.chunk_ids)

    def test_catan_searcher_has_catan_chunks(self) -> None:
        from api.main import _get_searcher

        searcher = _get_searcher("catan")
        if searcher is None:
            pytest.skip("Catan BM25 not ingested")
        assert all("catan" in cid for cid in searcher.chunk_ids)

    def test_searchers_are_independent(self) -> None:
        from api.main import _get_searcher

        s1 = _get_searcher("splendor")
        s2 = _get_searcher("catan")
        if s1 is None or s2 is None:
            pytest.skip("Both games must be ingested")
        assert s1.game_name != s2.game_name
        assert set(s1.chunk_ids).isdisjoint(set(s2.chunk_ids))
