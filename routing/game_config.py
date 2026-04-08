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
    "catan": GameConfig(
        retrieval_hops=1,
        rerank_top_k=5,
        hybrid_top_k=20,
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=False,
        version_aware=False,
        parser_mode="cost_effective",
    ),
    # Phase 2+
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


TERMINOLOGY_MAPS: dict[str, dict[str, str]] = {
    "splendor": {
        "gold token": "gold joker token",
        "wild": "gold joker token",
        "wildcard": "gold joker token",
        "gems": "gem tokens",
        "jewels": "gem tokens",
        "points": "prestige points",
        "victory points": "prestige points",
        "reserve": "reserve a development card",
        "hold a card": "reserve a development card",
        "nobles": "noble tiles",
        "noble visit": "noble tiles",
        "buy": "purchase a development card",
        "card bonus": "bonus",
        "discount": "bonus",
    },
    "catan": {
        "steal": "take 1 random resource card (robber)",
        "rob": "robber",
        "trade with bank": "maritime trade",
        "trade with players": "domestic trade",
        "soldier": "knight card",
        "soldier card": "knight card",
        "upgrade": "upgrade to a city",
        "upgrade settlement": "upgrade to a city",
        "wheat": "grain",
        "corn": "grain",
        "sheep": "wool",
        "wood": "lumber",
    },
}


def get_terminology_map(game_name: str) -> dict[str, str]:
    return TERMINOLOGY_MAPS.get(game_name.lower().strip(), {})


def get_config(game_name: str) -> GameConfig:
    game_name = game_name.lower().strip()
    if game_name not in GAME_CONFIG:
        raise ValueError(f"Unknown game: {game_name}. Available: {list(GAME_CONFIG.keys())}")
    return GAME_CONFIG[game_name]
