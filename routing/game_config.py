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
    tier2_threshold: float = 0.10  # Below tier1, above this = Tier 2 multi-hop candidate


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
        retrieval_hops=2,  # Phase 2b: 2-hop multi-hop
        rerank_top_k=5,
        hybrid_top_k=40,  # Larger corpus (185 chunks) needs wider net
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=False,
        version_aware=False,
        parser_mode="agentic",
        tier1_threshold=0.15,  # Lower for domain-specific proper nouns
        tier2_threshold=0.08,  # Lower because cross-encoder scores are lower for Speakeasy
    ),
    # Phase 2+
    "fcm": GameConfig(
        retrieval_hops=3,
        rerank_top_k=8,
        hybrid_top_k=40,
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=False,
        version_aware=False,
        parser_mode="agentic",
        tier1_threshold=0.20,
        tier2_threshold=0.08,
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
        "nightclub": "Nightclub",
        "distillery": "Stills",
        "booze": "barrels",
        "alcohol": "barrels",
        "liquor": "barrels",
    },
    "fcm": {
        "employees": "employee cards",
        "workers": "employee cards",
        "hire": "recruit",
        "fire": "fire (Phase 5: Payday)",
        "salary": "pay $5 for each card with salary icon",
        "money": "cash",
        "bank": "bank pool",
        "income": "unit price + bonuses",
        "demand": "demand counters on house",
        "supply": "food and drinks stock",
        "advertising": "marketing campaign",
        "billboard": "billboard campaign",
        "radio": "radio campaign",
        "airplane": "airplane campaign",
        "mailbox": "mailbox campaign",
        "upgrade": "train (employee training)",
        "promote": "train (employee training)",
        "level up": "train (employee training)",
        "garden bonus": "garden doubles unit price",
        "double price": "garden doubles unit price",
        "range": "range (number of tile crossings)",
        "org chart": "company structure",
        "pyramid": "company structure",
        "bench": "on the beach",
        "reserve": "on the beach",
        "break the bank": "bank breaks",
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
    "fcm": [("data/rulebooks/fcm.pdf", "fcm_rules")],
}


# Canonical location names per game (for location-aware chunk promotion)
LOCATION_NAMES: dict[str, frozenset[str]] = {
    "speakeasy": frozenset({
        "Contractor", "City Planner", "Garage", "City Hall",
        "Commission", "Docks", "Restaurant", "Park",
    }),
}


def get_pdf_sources(game_name: str) -> list[tuple[str, str]]:
    return PDF_SOURCES.get(game_name.lower().strip(), [])


def get_location_names(game_name: str) -> frozenset[str]:
    return LOCATION_NAMES.get(game_name.lower().strip(), frozenset())


def get_terminology_map(game_name: str) -> dict[str, str]:
    return TERMINOLOGY_MAPS.get(game_name.lower().strip(), {})


def get_config(game_name: str) -> GameConfig:
    game_name = game_name.lower().strip()
    if game_name not in GAME_CONFIG:
        raise ValueError(f"Unknown game: {game_name}. Available: {list(GAME_CONFIG.keys())}")
    return GAME_CONFIG[game_name]
