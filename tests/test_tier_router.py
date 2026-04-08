import math

from routing.tier_router import TierDecision, route_tier, sigmoid


class TestSigmoid:
    def test_zero_input(self) -> None:
        assert abs(sigmoid(0.0) - 0.5) < 1e-9

    def test_large_positive(self) -> None:
        assert sigmoid(10.0) > 0.999

    def test_large_negative(self) -> None:
        assert sigmoid(-10.0) < 0.001

    def test_symmetry(self) -> None:
        assert abs(sigmoid(2.0) + sigmoid(-2.0) - 1.0) < 1e-9


class TestRouteTier:
    def test_tier1_high_score(self) -> None:
        result = route_tier(cross_encoder_logit=2.0, threshold=0.85)
        assert result.tier == 1
        assert result.relevance_score > 0.85

    def test_tier3_low_score(self) -> None:
        result = route_tier(cross_encoder_logit=-1.0, threshold=0.85)
        assert result.tier == 3
        assert result.relevance_score <= 0.85

    def test_tier3_at_threshold(self) -> None:
        # sigmoid(x) == 0.85 when x = ln(0.85/0.15) ≈ 1.7346
        logit_at_threshold = math.log(0.85 / 0.15)
        result = route_tier(cross_encoder_logit=logit_at_threshold, threshold=0.85)
        # At exactly the threshold, score is not > threshold, so Tier 3
        assert result.tier == 3

    def test_just_above_threshold(self) -> None:
        logit_at_threshold = math.log(0.85 / 0.15)
        result = route_tier(cross_encoder_logit=logit_at_threshold + 0.1, threshold=0.85)
        assert result.tier == 1

    def test_returns_frozen_dataclass(self) -> None:
        result = route_tier(cross_encoder_logit=1.0)
        assert isinstance(result, TierDecision)

    def test_custom_threshold(self) -> None:
        result = route_tier(cross_encoder_logit=0.0, threshold=0.4)
        assert result.tier == 1
        assert abs(result.relevance_score - 0.5) < 1e-9

    def test_default_threshold_is_085(self) -> None:
        # sigmoid(2.0) ≈ 0.88 > 0.85 → Tier 1
        result = route_tier(cross_encoder_logit=2.0)
        assert result.tier == 1
