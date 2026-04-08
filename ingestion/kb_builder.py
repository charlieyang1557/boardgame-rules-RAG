from __future__ import annotations

import os
import pickle
from dataclasses import dataclass

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()


@dataclass(frozen=True)
class KBBuildResult:
    chunk_count: int
    pinecone_count: int
    bm25_count: int


def _embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed texts using OpenAI text-embedding-3-large."""
    from openai import OpenAI

    client = OpenAI()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model="text-embedding-3-large", input=batch)
        for item in response.data:
            all_embeddings.append(item.embedding)

    return all_embeddings


def _upsert_to_pinecone(
    chunks: list[dict],
    embeddings: list[list[float]],
    game_name: str,
    batch_size: int = 20,
) -> int:
    """Upsert chunk embeddings to Pinecone index."""
    from pinecone import Pinecone

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    index_name = "boardgame-oracle"
    # Create index if it doesn't exist
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=3072,
            metric="cosine",
            spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
        )

    index = pc.Index(index_name)

    # Upsert in batches
    upserted = 0
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        batch_embeddings = embeddings[i : i + batch_size]
        vectors = []
        for chunk, emb in zip(batch_chunks, batch_embeddings):
            vectors.append({
                "id": chunk["chunk_id"],
                "values": emb,
                "metadata": {
                    "game_name": chunk["game_name"],
                    "section": chunk["section"],
                    "page": chunk["page"],
                    "text": chunk["text"][:1000].encode("ascii", errors="replace").decode("ascii"),
                },
            })
        index.upsert(vectors=vectors, namespace=game_name)
        upserted += len(vectors)

    return upserted


def _build_bm25_index(chunks: list[dict], game_name: str) -> int:
    """Build BM25 index from chunk texts and pickle it."""
    tokenized_corpus = [chunk["text"].lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    # Store the BM25 object + chunk metadata together
    bm25_data = {
        "bm25": bm25,
        "chunk_ids": [c["chunk_id"] for c in chunks],
        "chunk_texts": [c["text"] for c in chunks],
        "chunk_count": len(chunks),
    }

    pickle_path = f"ingestion/cache/{game_name}_bm25.pkl"
    os.makedirs(os.path.dirname(pickle_path), exist_ok=True)
    with open(pickle_path, "wb") as f:
        pickle.dump(bm25_data, f)

    return len(chunks)


def build_primary_kb(game_name: str, pdf_path: str) -> KBBuildResult:
    """Full ingestion pipeline: parse → chunk → embed → upsert + BM25.

    Args:
        game_name: Lowercase game identifier (e.g., "splendor").
        pdf_path: Path to the rulebook PDF.

    Returns:
        KBBuildResult with counts for validation.
    """
    from ingestion.chunker import chunk_parsed_pages
    from ingestion.pdf_parser import parse_pdf
    from routing.game_config import get_config

    config = get_config(game_name)

    # Parse PDF
    pages = parse_pdf(pdf_path, game_name, mode=config.parser_mode)

    # Chunk
    chunks = chunk_parsed_pages(pages, game_name, chunk_size=150, overlap=30)
    if not chunks:
        raise ValueError(f"No chunks produced from {pdf_path}")

    # Embed
    texts = [c["text"] for c in chunks]
    embeddings = _embed_texts(texts)

    # Upsert to Pinecone
    pinecone_count = _upsert_to_pinecone(chunks, embeddings, game_name)

    # Build BM25 index
    bm25_count = _build_bm25_index(chunks, game_name)

    return KBBuildResult(
        chunk_count=len(chunks),
        pinecone_count=pinecone_count,
        bm25_count=bm25_count,
    )


def build_secondary_kb(game_name: str) -> None:
    """Secondary KB — not implemented until Phase 2."""
    raise NotImplementedError("Secondary KB not implemented until Phase 2")
