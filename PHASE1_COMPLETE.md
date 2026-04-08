# BoardGameOracle Phase 1 — Completion Report

## Metrics

### Tier Distribution (Golden Dataset, 30 queries)
- **Tier 1**: 25/30 (83%)
- **Tier 3**: 5/30 (17%)
- Target was 90% Tier 1 / 10% Tier 3

### Retrieval Quality
- Reranker sigmoid scores: median 0.979, mean 0.884
- 28/30 queries (93%) score above 0.50 threshold
- 2 genuine Tier 3 misses (information not well-captured in chunks)
- 3 borderline misses due to pipeline non-determinism

### Cache Performance
- Exact query cache hit: 281ms vs 6753ms uncached (24x speedup)
- Semantic similarity cache hit (paraphrase): 244ms
- Threshold 0.92 cosine similarity

### Forbidden Content
- 4/30 violations (all from Tier 3 responses which return raw chunks)
- No forbidden content in Tier 1 LLM-generated answers

### Hallucinations
- 0 detected in Tier 1 answers (citation verifier enforces inline citations)
- Tier 3 never generates — returns raw chunks only

### Query Logging
- Every query logged to SQLite with full metadata
- Feedback endpoint operational

## Calibrated Threshold
- **Threshold: 0.50** (sigmoid-normalized cross-encoder score)
- Bimodal distribution: 28/30 queries > 0.79, 2/30 < 0.04
- Clean separation — no queries in the 0.04–0.79 gap except 3 borderline

## Architecture Summary
```
User Query
    → Embed raw query (OpenAI text-embedding-3-large)
    → Semantic cache check (cosine > 0.92)
    → Query rewrite (Claude Haiku)
    → Embed rewritten query
    → Hybrid search (Pinecone dense + BM25 sparse + RRF fusion)
    → Cross-encoder rerank (ms-marco-MiniLM-L-6-v2, top-20 → top-5)
    → Tier route (sigmoid > 0.50 → Tier 1, else Tier 3)
    → Generate (Tier 1: Claude Sonnet with citations / Tier 3: raw chunks)
    → Citation verify (string overlap + Sonnet entailment)
    → Log to SQLite
    → Return response
```

## Test Suite
- **86 unit tests**, all passing
- Covers: tier router, query logger, chunker, hybrid search (RRF), reranker,
  generator, citation verifier, semantic cache, session manager, query rewriter,
  FastAPI endpoints

## Ingestion Stats
- Splendor rulebook: 4 pages, ~10K chars
- 20 chunks at 150-token size with 30-token overlap
- Context prefix: `[Splendor - Section]` embedded in every chunk
- Pinecone: 20 vectors (3072 dims) in `splendor` namespace
- BM25: pickled index with 20 documents

## Known Limitations (Phase 2 targets)
1. **Tier 1 accuracy at 83%** (target 90%) — 3 borderline queries route to Tier 3
   due to non-determinism between calibration and pipeline runs
2. **No Tier 2 (multi-hop)** — stubbed, ~35% of queries would benefit
3. **No RAGAS evaluation** — golden dataset only, no LLM-as-judge metrics
4. **Small chunk count** (20) — Splendor rules are short; larger rulebooks
   will produce hundreds of chunks
5. **No community rulings** (BGG) in Tier 3 output
6. **Unicode in chunks** — some special characters (smart quotes) replaced with `?`
   in Pinecone metadata due to ASCII encoding workaround
7. **Cache only saves embedding API cost** — every query still hits OpenAI
   for embedding before cache check

## File Count
- 12 source modules + 10 test files
- All files < 400 lines
- pyproject.toml with full dependency management

## Commits
```
50ecb16 fix: cache on raw query embedding (before rewriting) for deterministic cache hits
a49dec7 feat: calibrate tier router threshold to 0.50 based on golden dataset distribution
14c03bf fix: reduce chunk size to 150 tokens for better retrieval precision, ASCII-encode metadata
62b1605 fix: address code review — input validation, null guards, pickle safety, cache bounds, error leaks
ca902a9 feat: query rewriter (Haiku) and session manager with token budgeting
94b6b26 feat: FastAPI layer with /ask, /health, /api/feedback endpoints
55f3c51 feat: Tier 1/3 generator and two-step citation verifier
ae2bd60 feat: hybrid search (Pinecone + BM25 + RRF) and cross-encoder reranker
86f1317 feat: semantic cache with brute-force cosine similarity
6ec15e6 feat: golden dataset (30 Splendor Q&A) and eval runner skeleton
2292c84 feat: ingestion pipeline — PDF parser, chunker, KB builder
b285c59 feat: SQLite query logger with feedback support
2f6e754 feat: game config and tier router with sigmoid scoring
2ffb390 chore: initial project scaffolding
```
