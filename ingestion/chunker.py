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


def _split_by_headings(text: str, max_section_tokens: int) -> list[tuple[str, str]]:
    """Split text on markdown headings. Returns list of (heading, body) tuples.

    If a section exceeds max_section_tokens, it will be split further by
    the regular _split_text function downstream. Sections under the limit
    are kept as coherent units.
    """
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            # Flush previous section
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = re.sub(r"^#+\s*", "", stripped).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(h, b) for h, b in sections if b]


def _create_milestone_index(chunks: list[dict], game_name: str) -> dict | None:
    """Create a synthetic Milestone Index chunk if individual milestone chunks exist."""
    milestone_chunks = [
        c for c in chunks
        if "milestone" in c.get("section", "").lower()
        and "index" not in c.get("section", "").lower()
    ]
    if len(milestone_chunks) < 2:
        return None

    game_display = game_name.upper() if len(game_name) <= 4 else game_name.title()
    lines = [f"[{game_display} - Milestone Index] Summary of all milestones:"]
    for mc in milestone_chunks:
        # Extract first sentence as summary
        text = mc["text"]
        # Strip the prefix if present
        if "]" in text:
            text = text.split("]", 1)[1].strip()
        summary = text.split(".")[0] + "."
        lines.append(f"- {summary}")

    return {
        "chunk_id": f"{game_name}_milestone_index",
        "text": "\n".join(lines),
        "game_name": game_name,
        "section": "Milestone Index",
        "page": milestone_chunks[0].get("page", 0),
        "source_pdf": milestone_chunks[0].get("source_pdf", ""),
    }


def chunk_parsed_pages(
    pages: list[dict],
    game_name: str,
    chunk_size: int = 400,
    overlap: int = 50,
    source_pdf: str = "",
) -> list[dict]:
    """Split parsed PDF pages into context-enriched chunks.

    Every chunk gets a prefix like "[Splendor - Noble Tiles] " embedded
    directly in the text body for better retrieval.

    Section-aware: respects markdown heading boundaries from LlamaParse output.
    Sections under chunk_size * 2 tokens are kept as single coherent chunks.

    Args:
        pages: Output from pdf_parser.parse_pdf (list of {page, text, section}).
        game_name: Lowercase game identifier.
        chunk_size: Target chunk size in tokens.
        overlap: Overlap between consecutive chunks in tokens.
        source_pdf: Source PDF identifier for multi-PDF games.

    Returns:
        List of chunk dicts with keys: chunk_id, text, game_name, section, page, source_pdf.
    """
    game_display = game_name.title()
    all_chunks: list[dict] = []
    global_idx = 0

    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"].strip()
        page_section = page_data.get("section", "General")

        if not text:
            continue

        # Split by headings to respect section boundaries
        heading_sections = _split_by_headings(text, chunk_size * 2)
        if not heading_sections:
            heading_sections = [("", text)]

        for heading, body in heading_sections:
            section = heading or page_section
            body_tokens = _count_tokens(body)

            # If section fits in chunk_size * 2, keep it as one chunk
            if body_tokens <= chunk_size * 2:
                raw_chunks = [body]
            else:
                raw_chunks = _split_text(body, chunk_size, overlap)

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
                    "source_pdf": source_pdf,
                })
                global_idx += 1

    # Generate milestone index for games with milestone chunks
    index_chunk = _create_milestone_index(all_chunks, game_name)
    if index_chunk is not None:
        all_chunks.append(index_chunk)

    return all_chunks
