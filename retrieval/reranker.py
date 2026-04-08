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

    def rerank(self, query: str, chunks: list[dict], top_k: int = 5) -> list[RerankResult]:
        """Rerank chunks using cross-encoder, return top-k with sigmoid scores.

        Args:
            query: The user query.
            chunks: List of dicts with at least 'chunk_id' and 'text' keys.
            top_k: Number of results to return.

        Returns:
            Top-k RerankResults sorted by sigmoid score descending.
        """
        if not chunks:
            return []

        pairs = [(query, chunk["text"]) for chunk in chunks]
        raw_scores = self.model.predict(pairs)

        results = []
        for chunk, raw_score in zip(chunks, raw_scores):
            sig_score = 1.0 / (1.0 + math.exp(-float(raw_score)))
            results.append(
                RerankResult(
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    raw_score=float(raw_score),
                    sigmoid_score=sig_score,
                )
            )

        results.sort(key=lambda r: r.sigmoid_score, reverse=True)
        return results[:top_k]
