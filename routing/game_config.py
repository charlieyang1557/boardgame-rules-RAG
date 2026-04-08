from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SectionRule:
    """Per-section chunking rule applied during ingestion."""
    keep_intact: bool = False          # Never split this section
    max_chunk_size: int = 0            # Override default chunk size (0 = use game default)
    split_pattern: str = ""            # Regex to split section into individual items
    item_name_pattern: str = ""        # Regex to extract item name for chunk ID
    create_index: bool = False         # Generate a synthetic summary chunk


@dataclass(frozen=True)
class IngestionConfig:
    """Per-game ingestion settings: chunk sizes, section relabeling, and section rules."""
    chunk_size: int = 150
    overlap: int = 30
    section_patterns: dict[str, str] = field(default_factory=dict)   # regex → section name
    section_rules: dict[str, SectionRule] = field(default_factory=dict)  # section name → rule


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
    # FCM thresholds calibrated on golden dataset (2026-04-08):
    # Tier 1 scores: min=0.050, p10=0.123, median=0.938
    # Tier 2 scores: min=0.038, p10=0.817, median=0.991
    # Tier 3 scores: min=0.107, median=0.821
    # Scores are bimodal with heavy overlap — citation verification
    # is the primary quality gate, not the threshold.
    # Chosen: tier1=0.10 (captures 94% of T1), tier2=0.05 (minimal T3 false positives)
    "fcm": GameConfig(
        retrieval_hops=3,
        rerank_top_k=8,
        hybrid_top_k=40,
        rrf_k=60,
        multi_system_detection=False,
        use_secondary_kb=False,
        version_aware=False,
        parser_mode="agentic",
        tier1_threshold=0.10,
        tier2_threshold=0.05,
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


# Per-game ingestion configuration
INGESTION_CONFIGS: dict[str, IngestionConfig] = {
    "splendor": IngestionConfig(chunk_size=150, overlap=30),
    "catan": IngestionConfig(chunk_size=150, overlap=30),
    "speakeasy": IngestionConfig(chunk_size=300, overlap=50),
    # FCM: complex game needs section relabeling + custom chunking rules
    # Section patterns match raw parsed text body → assign section name.
    # Patterns are checked in order; first match wins per page.
    # Section carries forward across consecutive pages until a new match.
    # Section patterns are checked in order — first match wins.
    # More specific patterns MUST come before general ones.
    # Patterns are matched against the full page text body.
    "fcm": IngestionConfig(
        chunk_size=300,
        overlap=50,
        section_patterns={
            # Phase headers (most specific — match exact "Phase N:" format)
            r"Phase\s+4.*Dinnertime": "Phase 4 - Dinnertime",
            r"Phase\s+5.*Pay\s*day": "Phase 5 - Payday",
            r"Phase\s+6.*Marketing\s+campaign": "Phase 6 - Marketing Campaigns",
            r"Phase\s+7.*Clean": "Phase 7 - Clean Up",
            r"Phase\s+3.*Working": "Phase 3 - Working",
            r"Phase\s+2.*Hiring": "Phase 2 - Hiring",
            r"Phase\s+1.*Restructuring": "Phase 1 - Restructuring",
            # Milestones: require actual description language, not card labels
            r"(?:This|Th\s*is)\s+milestone\s+is\s+awarded": "Milestones",
            # Marketing campaigns: the "Initiate" section on page 9
            r"Initiate marketing campaign": "Marketing Campaigns",
            # Employee card grid (all-caps card names on page 6)
            r"WAITRESS\nPRICING": "Employee Cards",
            # Setup pages
            r"[Ff]illing the bank": "Setup",
            r"[Cc]ards setup\s*\n.*employee and milestone": "Setup",
            # Food & drinks production (part of Phase 3 Working)
            r"Get food.*drinks": "Phase 3 - Working",
            # Introductory game and strategy guide (page 15)
            r"[Ii]ntroductory\s*\n?\s*game": "Introductory Game",
            r"[Ss]trategy\s*\n?\s*[Gg]uide|[Ss]trategic pointer": "Strategy Guide",
            # Concepts page (page 4)
            r"[Cc]oncepts\s*\n.*[Ee]mployee cards": "Concepts",
        },
        section_rules={
            "Phase 4 - Dinnertime": SectionRule(keep_intact=True, max_chunk_size=1200),
            "Milestones": SectionRule(
                split_pattern=r"(?=First\s+(?:billboard|to\s+train|to\s+hire|burger|drink|cart|airplane|radio|to\s+have|to\s+lower|to\s+pay|to\s+throw))",
                create_index=True,
            ),
            "Marketing Campaigns": SectionRule(keep_intact=True, max_chunk_size=600),
            "Employee Cards": SectionRule(max_chunk_size=400),
            "Phase 1 - Restructuring": SectionRule(max_chunk_size=300),
            "Phase 2 - Hiring": SectionRule(max_chunk_size=300),
            "Phase 3 - Working": SectionRule(max_chunk_size=300),
            "Phase 5 - Payday": SectionRule(max_chunk_size=400),
            "Phase 6 - Marketing Campaigns": SectionRule(max_chunk_size=300),
            "Phase 7 - Clean Up": SectionRule(max_chunk_size=300),
            "Setup": SectionRule(max_chunk_size=300),
            "Introductory Game": SectionRule(max_chunk_size=400),
            "Strategy Guide": SectionRule(max_chunk_size=400),
        },
    ),
}


def get_ingestion_config(game_name: str) -> IngestionConfig:
    return INGESTION_CONFIGS.get(game_name.lower().strip(), IngestionConfig())


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
