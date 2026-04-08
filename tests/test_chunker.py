from ingestion.chunker import chunk_parsed_pages, _count_tokens, _split_text


class TestCountTokens:
    def test_empty_string(self) -> None:
        assert _count_tokens("") == 0

    def test_simple_text(self) -> None:
        tokens = _count_tokens("Hello world")
        assert tokens > 0

    def test_longer_text_has_more_tokens(self) -> None:
        short = _count_tokens("Hi")
        long = _count_tokens("This is a much longer piece of text with many words")
        assert long > short


class TestSplitText:
    def test_short_text_single_chunk(self) -> None:
        result = _split_text("Short text.", chunk_size=100, overlap=10)
        assert len(result) == 1
        assert result[0] == "Short text."

    def test_respects_chunk_size(self) -> None:
        long_text = ". ".join(["This is sentence number " + str(i) for i in range(50)]) + "."
        result = _split_text(long_text, chunk_size=50, overlap=10)
        assert len(result) > 1
        for chunk in result:
            # Allow some tolerance for overlap
            assert _count_tokens(chunk) < 80

    def test_empty_input(self) -> None:
        result = _split_text("", chunk_size=100, overlap=10)
        assert result == [] or result == [""]


class TestChunkParsedPages:
    def test_basic_chunking(self) -> None:
        pages = [
            {"page": 1, "text": "The game begins with setup. Each player takes tokens.", "section": "Setup"},
        ]
        chunks = chunk_parsed_pages(pages, "splendor", chunk_size=400, overlap=50)
        assert len(chunks) >= 1

    def test_context_prefix_in_text(self) -> None:
        pages = [
            {"page": 1, "text": "Players take turns clockwise.", "section": "Turn Order"},
        ]
        chunks = chunk_parsed_pages(pages, "splendor")
        assert all("[Splendor - Turn Order]" in c["text"] for c in chunks)

    def test_game_name_in_metadata(self) -> None:
        pages = [{"page": 1, "text": "Some text.", "section": "General"}]
        chunks = chunk_parsed_pages(pages, "splendor")
        assert all(c["game_name"] == "splendor" for c in chunks)

    def test_chunk_id_format(self) -> None:
        pages = [{"page": 1, "text": "Some text.", "section": "General"}]
        chunks = chunk_parsed_pages(pages, "splendor")
        for c in chunks:
            assert c["chunk_id"].startswith("splendor_p1_c")

    def test_chunk_ids_are_unique(self) -> None:
        pages = [
            {"page": 1, "text": ". ".join(["Sentence " + str(i) for i in range(100)]) + ".", "section": "Rules"},
        ]
        chunks = chunk_parsed_pages(pages, "splendor", chunk_size=50, overlap=10)
        ids = [c["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_empty_page_skipped(self) -> None:
        pages = [
            {"page": 1, "text": "", "section": "Empty"},
            {"page": 2, "text": "Content here.", "section": "Rules"},
        ]
        chunks = chunk_parsed_pages(pages, "splendor")
        assert all(c["page"] == 2 for c in chunks)

    def test_multiple_pages(self) -> None:
        pages = [
            {"page": 1, "text": "Page one content.", "section": "Setup"},
            {"page": 2, "text": "Page two content.", "section": "Gameplay"},
        ]
        chunks = chunk_parsed_pages(pages, "splendor")
        assert len(chunks) >= 2
        sections = {c["section"] for c in chunks}
        assert "Setup" in sections
        assert "Gameplay" in sections

    def test_default_section_general(self) -> None:
        pages = [{"page": 1, "text": "No section provided."}]
        chunks = chunk_parsed_pages(pages, "splendor")
        assert chunks[0]["section"] == "General"
