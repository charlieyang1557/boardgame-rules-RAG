from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TierDecision:
    tier: int
    relevance_score: float


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def route_tier(
    cross_encoder_logit: float,
    threshold: float = 0.25,
    tier2_threshold: float | None = None,
) -> TierDecision:
    """Three-tier routing based on sigmoid-normalized cross-encoder score.

    Args:
        cross_encoder_logit: Raw logit from cross-encoder reranker (best chunk).
        threshold: Sigmoid score above which Tier 1 is assigned.
        tier2_threshold: If set, scores between tier2_threshold and threshold
                         route to Tier 2 (multi-hop). If None, falls back to
                         binary Tier 1/3 routing.

    Returns:
        TierDecision with tier (1, 2, or 3) and the sigmoid relevance score.
    """
    score = sigmoid(cross_encoder_logit)
    if score > threshold:
        return TierDecision(tier=1, relevance_score=score)
    if tier2_threshold is not None and score > tier2_threshold:
        return TierDecision(tier=2, relevance_score=score)
    return TierDecision(tier=3, relevance_score=score)
