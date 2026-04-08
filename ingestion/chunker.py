from __future__ import annotations

import hashlib
import re

import tiktoken


_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


def _make_chunk_id(game_name: str, page: int, idx: int) -> str:
    """Deterministic chunk ID from game name, page number, and chunk index."""
    raw = f"{game_name}_{page}_{idx}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"{game_name}_p{page}_c{idx}_{short_hash}"


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into chunks by sentences, respecting token limits."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sent_tokens = _count_tokens(sentence)
        if sent_tokens > chunk_size:
            # Single sentence exceeds limit — force split by words
            if current:
                chunks.append(" ".join(current))
                current = []
                current_tokens = 0
            words = sentence.split()
            word_chunk: list[str] = []
            wt = 0
            for w in words:
                wt_new = _count_tokens(w)
                if wt + wt_new > chunk_size and word_chunk:
                    chunks.append(" ".join(word_chunk))
                    word_chunk = []
                    wt = 0
                word_chunk.append(w)
                wt += wt_new
            if word_chunk:
                chunks.append(" ".join(word_chunk))
            continue

        if current_tokens + sent_tokens > chunk_size and current:
            chunks.append(" ".join(current))
            # Overlap: keep last sentences that fit in overlap budget
            overlap_tokens = 0
            overlap_start = len(current)
            for j in range(len(current) - 1, -1, -1):
                st = _count_tokens(current[j])
                if overlap_tokens + st > overlap:
                    break
                overlap_tokens += st
                overlap_start = j
            current = current[overlap_start:]
            current_tokens = sum(_count_tokens(s) for s in current)

        current.append(sentence)
        current_tokens += sent_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_parsed_pages(
    pages: list[dict],
    game_name: str,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[dict]:
    """Split parsed PDF pages into context-enriched chunks.

    Every chunk gets a prefix like "[Splendor - Noble Tiles] " embedded
    directly in the text body for better retrieval.

    Args:
        pages: Output from pdf_parser.parse_pdf (list of {page, text, section}).
        game_name: Lowercase game identifier.
        chunk_size: Target chunk size in tokens.
        overlap: Overlap between consecutive chunks in tokens.

    Returns:
        List of chunk dicts with keys: chunk_id, text, game_name, section, page.
    """
    game_display = game_name.title()
    all_chunks: list[dict] = []
    global_idx = 0

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"].strip()
        section = page_data.get("section", "General")

        if not text:
            continue

        raw_chunks = _split_text(text, chunk_size, overlap)
        prefix = f"[{game_display} - {section}] "

        for chunk_text in raw_chunks:
            enriched_text = prefix + chunk_text
            chunk_id = _make_chunk_id(game_name, page_num, global_idx)
            all_chunks.append({
                "chunk_id": chunk_id,
                "text": enriched_text,
                "game_name": game_name,
                "section": section,
                "page": page_num,
            })
            global_idx += 1

    return all_chunks
