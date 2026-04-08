from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationResult:
    answer: str
    citations: list[dict]  # [{claim: str, chunk_id: str}]
    tier: int


TIER1_SYSTEM_PROMPT = """You are a board game rules expert. Answer the question using ONLY the provided rule chunks.

RULES FOR CITATIONS:
1. For every factual claim, cite the source using [chunk_id] format inline.
2. ONLY cite chunk IDs that appear in the provided chunks. Never invent or guess a chunk ID.
3. Use the EXACT terminology from the cited chunk text — do not substitute game terms
   with synonyms. If the chunk says "joker token", say "joker token", not "gold token".
4. State rules directly. Do NOT make meta-commentary about rules (e.g., do not say
   "this same rule is repeated elsewhere" or "the rules also confirm").
5. If the chunks don't contain enough information, say so explicitly.
6. Keep answers concise — state the rule, cite the chunk, move on."""


def generate_tier1(query: str, chunks: list[dict], anthropic_client) -> GenerationResult:
    context_parts = []
    for c in chunks:
        context_parts.append(f"[{c['chunk_id']}]: {c['text']}")
    context = "\n\n".join(context_parts)
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0,
        system=TIER1_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Valid chunk IDs: {', '.join(c['chunk_id'] for c in chunks)}\n\n"
                f"Rule chunks:\n{context}\n\n"
                f"Question: {query}"
            ),
        }],
    )
    answer = message.content[0].text
    import re
    citation_pattern = re.compile(r'\[([^\]]+)\]')
    found_ids = citation_pattern.findall(answer)
    valid_chunk_ids = {c["chunk_id"] for c in chunks}
    citations = [
        {"claim": "", "chunk_id": cid}
        for cid in found_ids
        if cid in valid_chunk_ids
    ]
    return GenerationResult(answer=answer, citations=citations, tier=1)


def generate_tier3(
    chunks: list[dict], anthropic_client=None, query: str = "",
) -> GenerationResult:
    """Tier 3: structured response with optional suggested interpretation.

    Uses Haiku (cheapest model) for the interpretation if available.
    Only generates interpretation if closest chunk has sigmoid > 0.05.
    """
    top_3 = chunks[:3]
    parts = ["The rule book does not address this directly.\n"]
    parts.append("Closest relevant rules found:\n")
    for i, c in enumerate(top_3, 1):
        score = c.get("sigmoid_score", c.get("score", 0.0))
        parts.append(f"{i}. [{c['chunk_id']}] (relevance: {score:.2f}): {c['text'][:300]}")

    # Suggested interpretation using Haiku (cheap)
    best_score = top_3[0].get("sigmoid_score", 0) if top_3 else 0
    if anthropic_client and query and best_score > 0.05:
        try:
            chunk_context = "\n".join(c["text"][:200] for c in top_3)
            msg = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                temperature=0,
                system="Based on the closest rule chunks, offer a brief suggested interpretation. Clearly label it as interpretation, not official rule.",
                messages=[{"role": "user", "content": f"Closest rules:\n{chunk_context}\n\nQuestion: {query}"}],
            )
            parts.append(f"\nSuggested interpretation (not an official rule):\n{msg.content[0].text}")
        except Exception:
            pass

    answer = "\n".join(parts)
    return GenerationResult(answer=answer, citations=[], tier=3)
