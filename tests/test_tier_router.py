import math

from routing.game_config import get_config, get_pdf_sources, get_terminology_map
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

    def test_default_threshold_is_025(self) -> None:
        # sigmoid(-1.0) ≈ 0.269 > 0.25 → Tier 1
        result = route_tier(cross_encoder_logit=-1.0)
        assert result.tier == 1

    def test_default_threshold_tier3(self) -> None:
        # sigmoid(-1.2) ≈ 0.232 < 0.25 → Tier 3 (no tier2_threshold set)
        result = route_tier(cross_encoder_logit=-1.2)
        assert result.tier == 3

    def test_tier2_between_thresholds(self) -> None:
        # sigmoid(-0.5) ≈ 0.378, tier1=0.5, tier2=0.10 → Tier 2
        result = route_tier(cross_encoder_logit=-0.5, threshold=0.5, tier2_threshold=0.10)
        assert result.tier == 2
        assert 0.10 < result.relevance_score < 0.5

    def test_tier2_above_tier1_goes_tier1(self) -> None:
        result = route_tier(cross_encoder_logit=2.0, threshold=0.5, tier2_threshold=0.10)
        assert result.tier == 1

    def test_tier2_below_tier2_goes_tier3(self) -> None:
        # sigmoid(-3.0) ≈ 0.047 < 0.10 → Tier 3
        result = route_tier(cross_encoder_logit=-3.0, threshold=0.5, tier2_threshold=0.10)
        assert result.tier == 3

    def test_no_tier2_threshold_falls_to_binary(self) -> None:
        # Without tier2_threshold, same as binary Tier 1/3
        result = route_tier(cross_encoder_logit=-0.5, threshold=0.5)
        assert result.tier == 3  # Not Tier 2


class TestFcmConfig:
    def test_fcm_config_exists(self) -> None:
        config = get_config("fcm")
        assert config.retrieval_hops == 3
        assert config.rerank_top_k == 8
        assert config.hybrid_top_k == 40
        assert config.parser_mode == "agentic"
        assert config.multi_system_detection is False
        assert config.use_secondary_kb is False

    def test_fcm_terminology_map(self) -> None:
        term_map = get_terminology_map("fcm")
        assert "employees" in term_map
        assert term_map["hire"] == "recruit"
        assert term_map["garden bonus"] == "garden doubles unit price"

    def test_fcm_pdf_sources(self) -> None:
        sources = get_pdf_sources("fcm")
        assert len(sources) == 1
        assert sources[0][1] == "fcm_rules"
