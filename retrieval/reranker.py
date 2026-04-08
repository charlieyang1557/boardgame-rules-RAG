from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RerankResult:
    chunk_id: str
    text: str
    raw_score: float
    sigmoid_score: float


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 5,
        alt_query: str | None = None,
    ) -> list[RerankResult]:
        """Rerank chunks using cross-encoder, return top-k with sigmoid scores.

        When alt_query is provided (dual-query reranking), each chunk is scored
        against both queries and the max sigmoid score is kept. This eliminates
        score variance introduced by query rewriting — zero extra API cost since
        the cross-encoder runs locally.

        Args:
            query: The primary query (typically the rewritten query).
            chunks: List of dicts with at least 'chunk_id' and 'text' keys.
            top_k: Number of results to return.
            alt_query: Optional alternate query (typically the raw user query).

        Returns:
            Top-k RerankResults sorted by sigmoid score descending.
        """
        if not chunks:
            return []

        pairs = [(query, chunk["text"]) for chunk in chunks]
        raw_scores = self.model.predict(pairs)

        # Dual-query: also score against alt_query, take max per chunk
        alt_scores = None
        if alt_query is not None and alt_query != query:
            alt_pairs = [(alt_query, chunk["text"]) for chunk in chunks]
            alt_scores = self.model.predict(alt_pairs)

        results = []
        for i, (chunk, raw_score) in enumerate(zip(chunks, raw_scores)):
            best_raw = float(raw_score)
            if alt_scores is not None:
                alt_raw = float(alt_scores[i])
                best_raw = max(best_raw, alt_raw)
            sig_score = 1.0 / (1.0 + math.exp(-best_raw))
            results.append(
                RerankResult(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    raw_score=best_raw,
                    sigmoid_score=sig_score,
                )
            )

        results.sort(key=lambda r: r.sigmoid_score, reverse=True)
        return results[:top_k]
