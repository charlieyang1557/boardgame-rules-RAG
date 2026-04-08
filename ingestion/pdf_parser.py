from __future__ import annotations

import json
import os
import re


def _cache_path(game_name: str) -> str:
    return f"ingestion/cache/{game_name}_parsed.json"


def _load_cache(game_name: str) -> list[dict] | None:
    path = _cache_path(game_name)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def _save_cache(game_name: str, pages: list[dict]) -> None:
    path = _cache_path(game_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(pages, f, indent=2)


def _parse_with_llamaparse(pdf_path: str, mode: str = "cost_effective") -> list[dict]:
    """Parse PDF using LlamaParse API. Raises on failure."""
    from llama_parse import LlamaParse

    parser = LlamaParse(
        result_type="markdown",
        parsing_instruction="Extract all text from this board game rulebook. Preserve section headers.",
        premium_mode=(mode == "agentic"),
    )
    documents = parser.load_data(pdf_path)

    pages: list[dict] = []
    for i, doc in enumerate(documents):
        text = doc.text
        # Try to extract section from first heading in the text
        section = _extract_section(text)
        pages.append({"page": i + 1, "text": text, "section": section})
    return pages


def _parse_with_pymupdf(pdf_path: str) -> list[dict]:
    """Parse PDF using PyMuPDF as fallback."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    pages: list[dict] = []
    for i, page in enumerate(doc):
        text = page.get_text()
        section = _extract_section(text)
        pages.append({"page": i + 1, "text": text, "section": section})
    doc.close()
    return pages


def _extract_section(text: str) -> str:
    """Extract section header from text. Returns 'General' if none found."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        # Markdown heading
        if line.startswith("#"):
            return re.sub(r"^#+\s*", "", line).strip()
        # All-caps line (common in rulebooks)
        if line.isupper() and 3 < len(line) < 60:
            return line.title()
    return "General"


def parse_pdf(
    pdf_path: str,
    game_name: str,
    mode: str = "cost_effective",
) -> list[dict]:
    """Parse a PDF rulebook, with caching and LlamaParse→PyMuPDF fallback.

    Args:
        pdf_path: Path to the PDF file.
        game_name: Lowercase game identifier (e.g., "splendor").
        mode: LlamaParse mode — "cost_effective" or "agentic".

    Returns:
        List of dicts with keys: page (int), text (str), section (str).
    """
    cached = _load_cache(game_name)
    if cached is not None:
        return cached

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Try LlamaParse first, fallback to PyMuPDF
    try:
        pages = _parse_with_llamaparse(pdf_path, mode=mode)
    except Exception:
        pages = _parse_with_pymupdf(pdf_path)

    _save_cache(game_name, pages)
    return pages
