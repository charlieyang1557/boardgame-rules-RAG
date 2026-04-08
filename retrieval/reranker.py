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
        location_names: frozenset[str] | None = None,
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
        top_results = results[:top_k]

        # Location-aware chunk promotion: if query contains an exact location
        # name and the matching chunk isn't in top-k, inject it at position 1.
        if location_names:
            query_lower = query.lower()
            alt_lower = alt_query.lower() if alt_query else ""
            matched_loc = [
                loc for loc in location_names
                if loc.lower() in query_lower or loc.lower() in alt_lower
            ]
            if matched_loc:
                top_ids = {r.chunk_id for r in top_results}
                for r in results:
                    if r.chunk_id in top_ids:
                        continue
                    if any(loc.lower() in r.text.lower() for loc in matched_loc):
                        top_results.insert(0, r)
                        top_results = top_results[:top_k]
                        break

                # Also promote: if matching chunk is in top-k but not #1, move to #1
                for i, r in enumerate(top_results):
                    if i == 0:
                        continue
                    if any(loc.lower() in r.text.lower() for loc in matched_loc):
                        top_results.insert(0, top_results.pop(i))
                        break

        return top_results
