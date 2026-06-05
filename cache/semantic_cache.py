from __future__ import annotations

import math


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticCache:
    """In-memory semantic cache using brute-force cosine similarity.

    Partitioned by (game_name, language) to prevent cross-game and
    cross-language cache hits — a Chinese user must never receive a cached
    English answer. Only caches Tier 1 responses. Tier 3 is never cached.
    Session-scoped — does not persist across restarts.
    """

    def __init__(self, threshold: float = 0.92, max_size: int = 1000) -> None:
        self.threshold = threshold
        self.max_size = max_size
        self.embeddings: list[list[float]] = []
        self.responses: list[dict] = []
        self.game_names: list[str] = []
        self.languages: list[str] = []

    def lookup(
        self, query_embedding: list[float], game_name: str = "", language: str = "en"
    ) -> dict | None:
        """Check cache for a semantically similar query within the same game
        and output language.

        Returns cached response dict if cosine similarity > threshold AND both
        game_name and language match, otherwise None.
        """
        if not self.embeddings:
            return None

        best_sim = -1.0
        best_idx = -1
        for i, cached_emb in enumerate(self.embeddings):
            if self.game_names[i] != game_name or self.languages[i] != language:
                continue
            sim = _cosine_similarity(query_embedding, cached_emb)
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        if best_sim > self.threshold:
            return self.responses[best_idx]
        return None

    def store(
        self,
        query_embedding: list[float],
        response: dict,
        tier: int,
        game_name: str = "",
        language: str = "en",
    ) -> None:
        """Store a response in cache. Only Tier 1 is cached. LRU eviction at max_size."""
        if tier != 1:
            return
        if len(self.embeddings) >= self.max_size:
            self.embeddings.pop(0)
            self.responses.pop(0)
            self.game_names.pop(0)
            self.languages.pop(0)
        self.embeddings.append(query_embedding)
        self.responses.append(response)
        self.game_names.append(game_name)
        self.languages.append(language)

    @property
    def size(self) -> int:
        return len(self.embeddings)

    def clear(self) -> None:
        self.embeddings.clear()
        self.responses.clear()
        self.game_names.clear()
        self.languages.clear()
