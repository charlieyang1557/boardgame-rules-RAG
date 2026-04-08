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


def _merge_consecutive_sections(pages: list[dict], keep_intact_sections: set[str]) -> list[dict]:
    """Merge consecutive pages with the same section when keep_intact is set.

    This handles multi-page sections like Dinnertime that must not be split.
    Pages with sections NOT in keep_intact_sections pass through unchanged.
    """
    if not keep_intact_sections:
        return pages

    merged: list[dict] = []
    i = 0
    while i < len(pages):
        page = pages[i]
        section = page.get("section", "General")

        if section in keep_intact_sections:
            # Merge consecutive pages with same section
            combined_text = page["text"]
            first_page = page["page"]
            j = i + 1
            while j < len(pages) and pages[j].get("section", "General") == section:
                combined_text += "\n\n" + pages[j]["text"]
                j += 1
            merged.append({
                "page": first_page,
                "text": combined_text,
                "section": section,
            })
            i = j
        else:
            merged.append(page)
            i += 1

    return merged


def _apply_split_pattern(
    text: str, split_pattern: str, section: str, game_name: str,
    page_num: int, source_pdf: str, global_idx: int,
    item_name_pattern: str = "",
) -> tuple[list[dict], int]:
    """Split text by regex pattern into individual item chunks."""
    game_display = game_name.upper() if len(game_name) <= 4 else game_name.title()
    items = re.split(split_pattern, text)
    items = [item.strip() for item in items if item.strip()]

    chunks: list[dict] = []
    name_re = re.compile(item_name_pattern) if item_name_pattern else None

    for item_text in items:
        # Extract item name for section label
        item_name = ""
        if name_re:
            m = name_re.search(item_text)
            if m:
                item_name = m.group(0).strip()
        if not item_name:
            # Use first line as item name
            first_line = item_text.split("\n")[0].strip()
            # Truncate to reasonable length
            item_name = first_line[:60]

        item_section = f"{section} - {item_name}" if item_name else section
        prefix = f"[{game_display} - {item_section}] "
        enriched = prefix + item_text
        chunk_id = _make_chunk_id(game_name, page_num, global_idx)
        chunks.append({
            "chunk_id": chunk_id,
            "text": enriched,
            "game_name": game_name,
            "section": item_section,
            "page": page_num,
            "source_pdf": source_pdf,
        })
        global_idx += 1

    return chunks, global_idx


def chunk_parsed_pages(
    pages: list[dict],
    game_name: str,
    chunk_size: int = 400,
    overlap: int = 50,
    source_pdf: str = "",
    section_rules: dict | None = None,
) -> list[dict]:
    """Split parsed PDF pages into context-enriched chunks.

    Every chunk gets a prefix like "[Splendor - Noble Tiles] " embedded
    directly in the text body for better retrieval.

    Section-aware: respects markdown heading boundaries from LlamaParse output.
    Applies per-section rules (keep_intact, split_pattern, max_chunk_size)
    when section_rules is provided.

    Args:
        pages: Output from pdf_parser.parse_pdf (list of {page, text, section}).
        game_name: Lowercase game identifier.
        chunk_size: Target chunk size in tokens.
        overlap: Overlap between consecutive chunks in tokens.
        source_pdf: Source PDF identifier for multi-PDF games.
        section_rules: Dict mapping section name to SectionRule. If None, default chunking.

    Returns:
        List of chunk dicts with keys: chunk_id, text, game_name, section, page, source_pdf.
    """
    rules = section_rules or {}

    # Pre-chunk merge: combine consecutive pages for keep_intact sections
    keep_intact_sections = {name for name, rule in rules.items() if rule.keep_intact}
    pages = _merge_consecutive_sections(pages, keep_intact_sections)

    game_display = game_name.upper() if len(game_name) <= 4 else game_name.title()
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
            rule = rules.get(section)

            # Determine effective chunk size for this section
            effective_chunk_size = chunk_size
            if rule and rule.max_chunk_size > 0:
                effective_chunk_size = rule.max_chunk_size

            # Apply split_pattern if configured (e.g., milestones)
            if rule and rule.split_pattern:
                item_chunks, global_idx = _apply_split_pattern(
                    body, rule.split_pattern, section, game_name,
                    page_num, source_pdf, global_idx,
                    item_name_pattern=rule.item_name_pattern,
                )
                all_chunks.extend(item_chunks)
                continue

            # Keep intact: one chunk regardless of size
            if rule and rule.keep_intact:
                prefix = f"[{game_display} - {section}] "
                enriched_text = prefix + body
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
                continue

            # Default chunking with effective chunk size
            body_tokens = _count_tokens(body)
            if body_tokens <= effective_chunk_size * 2:
                raw_chunks = [body]
            else:
                raw_chunks = _split_text(body, effective_chunk_size, overlap)

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

    # Generate index chunks for sections with create_index=True
    for section_name, rule in rules.items():
        if rule.create_index:
            index_chunk = _create_milestone_index(
                [c for c in all_chunks if section_name.lower() in c.get("section", "").lower()],
                game_name,
            )
            if index_chunk is not None:
                all_chunks.append(index_chunk)

    # Fallback: also check for milestone chunks without explicit rules
    if not any(r.create_index for r in rules.values()):
        index_chunk = _create_milestone_index(all_chunks, game_name)
        if index_chunk is not None:
            all_chunks.append(index_chunk)

    return all_chunks
