from __future__ import annotations

from dataclasses import dataclass

REWRITE_SYSTEM_PROMPT = """You rewrite board game rules questions for retrieval.
Identify the board game being discussed.
Replace colloquial or ambiguous terms with precise rules terminology when possible.
Resolve pronouns and other coreferences using the provided history.
Output exactly two lines in this format:
GAME: <game name>
QUERY: <rewritten query>"""


@dataclass(frozen=True)
class RewriteResult:
    rewritten_query: str
    game_name: str


def rewrite_query(
    raw_query: str,
    history: str,
    anthropic_client,
    default_game: str = "splendor",
) -> RewriteResult:
    try:
        if history:
            user_content = f"Conversation history:\n{history}\n\nLatest user query:\n{raw_query}"
        else:
            user_content = f"Latest user query:\n{raw_query}"

        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=REWRITE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        text = "".join(
            block.text for block in getattr(response, "content", []) if hasattr(block, "text")
        )
        parsed_game = default_game
        parsed_query = raw_query

        for line in text.splitlines():
            if line.startswith("GAME:"):
                parsed_game = line.partition(":")[2].strip() or default_game
            if line.startswith("QUERY:"):
                parsed_query = line.partition(":")[2].strip() or raw_query

        return RewriteResult(rewritten_query=parsed_query, game_name=parsed_game)
    except Exception:
        return RewriteResult(rewritten_query=raw_query, game_name=default_game)
