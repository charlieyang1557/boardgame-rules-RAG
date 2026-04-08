from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    retrieval_hops: int
    rerank_top_k: int
    hybrid_top_k: int
    rrf_k: int
    multi_system_detection: bool
    use_secondary_kb: bool
    version_aware: bool
    parser_mode: str


GAME_CONFIG: dict[str, GameConfig] = {
    "splendor": GameConfig(
        retrieval_hops=1,
        rerank_top_k=5,
        hybrid_top_k=20,
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=False,
        version_aware=False,
        parser_mode="cost_effective",
    ),
    "speakeasy": GameConfig(
        retrieval_hops=2,
        rerank_top_k=5,
        hybrid_top_k=30,
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=True,
        version_aware=True,
        parser_mode="agentic",
    ),
    "fcm": GameConfig(
        retrieval_hops=3,
        rerank_top_k=8,
        hybrid_top_k=40,
        rrf_k=60,
        multi_system_detection=True,
        use_secondary_kb=True,
        version_aware=False,
        parser_mode="agentic",
    ),
}


def get_config(game_name: str) -> GameConfig:
    game_name = game_name.lower().strip()
    if game_name not in GAME_CONFIG:
        raise ValueError(f"Unknown game: {game_name}. Available: {list(GAME_CONFIG.keys())}")
    return GAME_CONFIG[game_name]
