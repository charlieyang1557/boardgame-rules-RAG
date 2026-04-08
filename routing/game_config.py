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
    tier1_threshold: float = 0.25  # Per-game sigmoid threshold for Tier 1 routing


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
    "speakeasy": GameConfig(
        retrieval_hops=1,  # Phase 2a: single hop only
        rerank_top_k=5,
        hybrid_top_k=40,  # Larger corpus (185 chunks) needs wider net
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=False,  # Phase 2b
        version_aware=False,
        parser_mode="agentic",
        tier1_threshold=0.15,  # Lower for domain-specific proper nouns
    ),
    # Phase 2+
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
    "speakeasy": {
        "worker": "Capo",
        "workers": "Capos",
        "meeple": "Family Member",
        "thug": "Goon",
        "thugs": "Goons",
        "protection money": "Leverage",
        "fame": "Infamy",
        "reputation": "Infamy",
        "running": "Operating",
        "open": "Operating",
        "gang war": "Mob War",
        "territory": "Zone Control",
        "district control": "Zone Control",
        "scoring": "Cooking Books",
        "end game scoring": "Cooking Books",
        "bar": "Speakeasy",
        "club": "Nightclub",
        "distillery": "Stills",
        "booze": "barrels",
        "alcohol": "barrels",
        "liquor": "barrels",
    },
}

# Multi-PDF source definitions per game
PDF_SOURCES: dict[str, list[tuple[str, str]]] = {
    "splendor": [("data/rulebooks/splendor.pdf", "splendor_rules")],
    "catan": [("data/rulebooks/catan.pdf", "catan_rules")],
    "speakeasy": [
        ("data/rulebooks/speakeasy_rules_v18.pdf", "speakeasy_rules"),
        ("data/rulebooks/speakeasy_player_aid.pdf", "speakeasy_player_aid"),
        ("data/rulebooks/speakeasy_solo_rules.pdf", "speakeasy_solo"),
        ("data/rulebooks/speakeasy_stretch_goals.pdf", "speakeasy_stretch"),
    ],
}


def get_pdf_sources(game_name: str) -> list[tuple[str, str]]:
    return PDF_SOURCES.get(game_name.lower().strip(), [])


def get_terminology_map(game_name: str) -> dict[str, str]:
    return TERMINOLOGY_MAPS.get(game_name.lower().strip(), {})


def get_config(game_name: str) -> GameConfig:
    game_name = game_name.lower().strip()
    if game_name not in GAME_CONFIG:
        raise ValueError(f"Unknown game: {game_name}. Available: {list(GAME_CONFIG.keys())}")
    return GAME_CONFIG[game_name]
