from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TierDecision:
    tier: int
    relevance_score: float


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def route_tier(cross_encoder_logit: float, threshold: float = 0.50) -> TierDecision:
    """Binary tier routing based on sigmoid-normalized cross-encoder score.

    Args:
        cross_encoder_logit: Raw logit from cross-encoder reranker (best chunk).
        threshold: Sigmoid score above which Tier 1 is assigned. Default 0.50,
                   calibrated against Splendor golden dataset (bimodal distribution:
                   28/30 queries > 0.79, 2/30 < 0.04).

    Returns:
        TierDecision with tier (1 or 3) and the sigmoid relevance score.
    """
    score = sigmoid(cross_encoder_logit)
    tier = 1 if score > threshold else 3
    return TierDecision(tier=tier, relevance_score=score)
