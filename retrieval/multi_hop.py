from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HopResult:
    chunks: list[dict]
    is_answerable: bool
    answer: str  # If answerable, the cited answer. Otherwise empty.
    follow_up_query: str  # If not answerable, the follow-up search query.
    missing_info: str  # If not answerable, what info is missing.


@dataclass(frozen=True)
class ChainResult:
    merged_chunks: list[dict]
    answer: str
    hops_used: int
    is_answerable: bool


ANSWERABLE_CHECK_PROMPT = """You are answering a board game rules question that may require
information from multiple rule sections.

Here are the rule chunks retrieved so far:
{chunks_text}

{existing_ids_note}Question: {query}

Can you fully answer this question from the chunks above?
- If YES: provide the answer with [chunk_id] citations using EXACT terminology from chunks.
- If NO: state what specific information is missing, and formulate a follow-up search query.

IMPORTANT for follow-up queries:
- Output 3-8 keywords using EXACT game terminology from the rulebook.
- Do NOT write natural language sentences. Write keyword search terms only.

Respond in this EXACT format:
ANSWERABLE: yes/no
ANSWER: (if yes) your answer with [chunk_id] citations
MISSING: (if no) what information is needed
FOLLOW_UP_QUERY: (if no) keyword search terms"""

FINAL_GENERATION_PROMPT = """You are a board game rules expert. Answer the question using the
merged rule chunks from multiple retrieval hops. These chunks may come from different
sections of the rulebook.

RULES FOR CITATIONS:
1. Cite every factual claim using [chunk_id] format inline.
2. ONLY cite chunk IDs from this list: {chunk_ids}
3. Use EXACT terminology from the cited chunk text.
4. If chunks contain conflicting information, prefer the more specific rule
   and note the conflict.
5. State rules directly — no meta-commentary about the rulebook.
6. Keep answers concise.

Rule chunks:
{chunks_text}

Question: {query}"""


def _format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{c['chunk_id']}]: {c['text']}" for c in chunks)


def _parse_answerable_response(text: str) -> tuple[bool, str, str, str]:
    """Parse the ANSWERABLE/ANSWER/MISSING/FOLLOW_UP_QUERY response."""
    is_answerable = False
    answer = ""
    missing = ""
    follow_up = ""

    for line in text.split("\n"):
        line = line.strip()
        upper = line.upper()
        if upper.startswith("ANSWERABLE:"):
            val = line.split(":", 1)[1].strip().lower()
            is_answerable = val in ("yes", "true")
        elif upper.startswith("ANSWER:"):
            answer = line.split(":", 1)[1].strip()
        elif upper.startswith("MISSING:"):
            missing = line.split(":", 1)[1].strip()
        elif upper.startswith("FOLLOW_UP_QUERY:") or upper.startswith("FOLLOW_UP QUERY:"):
            follow_up = line.split(":", 1)[1].strip()

    # If answerable=yes but answer is on subsequent lines, collect them
    if is_answerable and not answer:
        in_answer = False
        for line in text.split("\n"):
            if line.strip().upper().startswith("ANSWER:"):
                in_answer = True
                answer = line.split(":", 1)[1].strip()
            elif in_answer and not line.strip().upper().startswith(("MISSING:", "FOLLOW_UP")):
                answer += " " + line.strip()
            elif in_answer:
                break

    return is_answerable, answer.strip(), missing, follow_up


class ChainOfRetrieval:
    """Multi-hop retrieval for Tier 2 queries.

    Performs up to max_hops retrieval rounds, using Sonnet to determine
    if additional information is needed between hops.
    """

    def __init__(self, searcher, reranker, anthropic_client, openai_client, max_hops: int = 2) -> None:
        self.searcher = searcher
        self.reranker = reranker
        self.anthropic_client = anthropic_client
        self.openai_client = openai_client
        self.max_hops = max_hops

    def _embed(self, text: str) -> list[float]:
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-large", input=text,
        )
        return response.data[0].embedding

    def _search_and_rerank(
        self, query: str, top_k: int = 5, alt_query: str | None = None,
        location_names: frozenset[str] | None = None,
        rrf_k: int = 60, hybrid_top_k: int = 20,
    ) -> list[dict]:
        emb = self._embed(query)
        results = self.searcher.search(query, emb, top_k=hybrid_top_k, rrf_k=rrf_k)
        chunks = [{"chunk_id": r.chunk_id, "text": r.text} for r in results]
        reranked = self.reranker.rerank(
            query, chunks, top_k=top_k,
            alt_query=alt_query, location_names=location_names,
        )
        return [{"chunk_id": r.chunk_id, "text": r.text, "sigmoid_score": r.sigmoid_score} for r in reranked]

    def _check_answerable(self, query: str, chunks: list[dict]) -> HopResult:
        chunks_text = _format_chunks(chunks)
        chunk_ids = [c["chunk_id"] for c in chunks]
        existing_ids_note = ""
        if chunk_ids:
            existing_ids_note = (
                f"Already retrieved chunk IDs (do NOT search for these again): "
                f"{', '.join(chunk_ids)}\n"
            )
        prompt = ANSWERABLE_CHECK_PROMPT.format(
            chunks_text=chunks_text,
            query=query,
            existing_ids_note=existing_ids_note,
        )

        message = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        is_answerable, answer, missing, follow_up = _parse_answerable_response(response_text)

        return HopResult(
            chunks=chunks,
            is_answerable=is_answerable,
            answer=answer,
            follow_up_query=follow_up,
            missing_info=missing,
        )

    def _generate_final(self, query: str, chunks: list[dict]) -> str:
        chunk_ids = ", ".join(c["chunk_id"] for c in chunks)
        chunks_text = _format_chunks(chunks)
        prompt = FINAL_GENERATION_PROMPT.format(
            chunk_ids=chunk_ids, chunks_text=chunks_text, query=query,
        )

        message = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _merge_chunks(self, hop1: list[dict], hop2: list[dict]) -> list[dict]:
        """Merge two chunk lists, dedup by chunk_id, keep higher score."""
        seen: dict[str, dict] = {}
        for c in hop1:
            seen[c["chunk_id"]] = c
        for c in hop2:
            cid = c["chunk_id"]
            if cid not in seen or c.get("sigmoid_score", 0) > seen[cid].get("sigmoid_score", 0):
                seen[cid] = c
        return list(seen.values())

    def retrieve_and_reason(
        self,
        query: str,
        game_name: str,
        config,
        alt_query: str | None = None,
        location_names: frozenset[str] | None = None,
        initial_chunks: list[dict] | None = None,
    ) -> ChainResult:
        """Multi-hop retrieval with reasoning steps.

        Iterates up to max_hops times, checking answerability at each hop.
        Terminates early if answerable or if no follow-up query is generated.
        """
        all_merged: list[dict] = []
        current_query = query

        for hop_num in range(1, self.max_hops + 1):
            # Search
            if hop_num == 1 and initial_chunks:
                hop_chunks = initial_chunks
            else:
                hop_chunks = self._search_and_rerank(
                    current_query, top_k=config.rerank_top_k,
                    alt_query=alt_query if hop_num == 1 else None,
                    location_names=location_names if hop_num == 1 else None,
                    rrf_k=config.rrf_k, hybrid_top_k=config.hybrid_top_k,
                )

            # Merge with previous hops
            all_merged = self._merge_chunks(all_merged, hop_chunks)

            # Check answerability
            hop_result = self._check_answerable(query, all_merged)

            if hop_result.is_answerable:
                return ChainResult(
                    merged_chunks=all_merged,
                    answer=hop_result.answer,
                    hops_used=hop_num,
                    is_answerable=True,
                )

            # Not answerable — check if we can continue
            if hop_num == self.max_hops or not hop_result.follow_up_query:
                # Max hops reached or no follow-up — generate best-effort
                answer = self._generate_final(query, all_merged)
                return ChainResult(
                    merged_chunks=all_merged,
                    answer=answer,
                    hops_used=hop_num,
                    is_answerable=True,
                )

            # Continue to next hop with follow-up query
            current_query = hop_result.follow_up_query

        # Safety fallback (should not reach)
        return ChainResult(
            merged_chunks=all_merged, answer="", hops_used=self.max_hops, is_answerable=False,
        )
