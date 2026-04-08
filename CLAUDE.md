# BoardGameOracle — RAG System for Board Game Rules

## Context
Build a RAG-based Q&A system that answers board game rules questions
with citations, multi-hop reasoning, and honest uncertainty handling.
Start with Phase 1: Splendor only. Architecture must support
Speakeasy and FCM in later phases without structural changes.

## Phase 1 Scope (Splendor only)
- Ingestion pipeline for PDF rulebooks
- Hybrid retrieval (dense embeddings + client-side BM25, manual RRF fusion)
- Reranking (cross-encoder, local)
- Tier 1 direct answer with citation verification
- Tier 3 honest uncertainty output (no generation — return closest chunks)
- Semantic cache layer (in-memory dict, brute-force cosine similarity)
- Basic conversation history (last 3 turns, max 2000 tokens)
- Structured query logging to SQLite
- User feedback endpoint
- Evaluation pipeline with golden dataset (no RAGAS in Phase 1)

## Tech Stack
- Vector DB: Pinecone serverless (free tier, dense vectors only)
- Sparse Search: Client-side BM25 via rank_bm25 library
- Hybrid Fusion: Client-side RRF (Reciprocal Rank Fusion) combining
  Pinecone dense results + local BM25 results
- Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2 (local, free, no API cost)
  Import: sentence_transformers.CrossEncoder
- Embeddings: text-embedding-3-large (OpenAI, 3072 dims)
- LLM (Query Rewriting): Claude Haiku via Anthropic SDK
- LLM (Generation + Verification): Claude Sonnet via Anthropic SDK
- PDF parsing: LlamaParse (primary), PyMuPDF (fallback)
- Evaluation: Golden dataset regression tests (RAGAS deferred to Phase 2)
- Query logging: SQLite (logs/query_log.db)
- Orchestration: Plain Python function composition (no LangGraph)
- Framework: FastAPI backend
- Dependency management: pyproject.toml with pip

## Project Structure
```
boardgame-oracle/
├── pyproject.toml           # Dependencies and project metadata
├── .env.example             # Template for required API keys
├── data/
│   └── rulebooks/
│       └── splendor.pdf     # User must place Splendor rulebook here
├── ingestion/
│   ├── __init__.py
│   ├── pdf_parser.py        # LlamaParse + PyMuPDF fallback
│   ├── chunker.py           # Context-enriched chunking
│   ├── kb_builder.py        # Primary KB only (Phase 1)
│   └── cache/               # {game}_parsed.json + {game}_bm25.pkl
├── retrieval/
│   ├── __init__.py
│   ├── hybrid_search.py     # Dense (Pinecone) + Sparse (BM25) + RRF
│   ├── reranker.py          # Cross-encoder reranking of top-20 → top-5
│   └── query_rewriter.py    # Haiku-based rewriting + coref resolution
├── routing/
│   ├── __init__.py
│   ├── tier_router.py       # Tier 1/3 binary decision
│   └── game_config.py       # Per-game configuration
├── generation/
│   ├── __init__.py
│   └── generator.py         # Tier 1 answer + Tier 3 fallback in one file
├── verification/
│   ├── __init__.py
│   └── citation_verifier.py # String overlap + LLM entailment check
├── cache/
│   ├── __init__.py
│   └── semantic_cache.py    # In-memory dict, brute-force cosine sim
├── conversation/
│   ├── __init__.py
│   └── session_manager.py   # Last 3 turns, max 2000 tokens, coref
├── query_logging/           # Renamed from logging/ to avoid stdlib shadow
│   ├── __init__.py
│   └── query_logger.py      # Structured SQLite logging per query
├── evaluation/
│   ├── __init__.py
│   ├── golden_dataset/
│   │   └── splendor.json
│   └── eval_runner.py       # Golden dataset regression tests
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI endpoints + GET /health
│   └── feedback.py          # User feedback endpoint
└── logs/                    # SQLite DB location (gitignored)
```

## Required API Keys (.env)
```
PINECONE_API_KEY=        # Pinecone serverless (free tier)
OPENAI_API_KEY=          # text-embedding-3-large
ANTHROPIC_API_KEY=       # Claude Haiku + Sonnet
LLAMA_CLOUD_API_KEY=     # LlamaParse (free tier: 1000 pages/day)
```
load_dotenv() must be called BEFORE any module imports that read env vars.

## Key Implementation Details

### Hybrid Search — Client-Side Architecture
Pinecone free tier supports dense vectors only. Hybrid search is
implemented client-side:
1. Query → OpenAI embedding → Pinecone top-20 by cosine similarity
2. Query → BM25 scoring against local chunk text index → top-20
3. Client-side RRF fusion: score = sum(1/(k+rank)) for k=60
   Each source contributes a ranked list of 20. RRF merges both lists,
   scores each unique chunk, takes the top-20 by fused score.
4. Combined top-20 → cross-encoder reranker → top-5

The BM25 index is pickled to ingestion/cache/{game_name}_bm25.pkl
during ingestion. Loaded into memory at startup.
Staleness guard: at startup, verify pickle chunk count == Pinecone
namespace vector count. If mismatch, refuse to start and log error.
Ingestion always regenerates the pickle (never append).

### Query Rewriting — Why It Matters
Users ask in oral language. Rule books are written in formal terminology.
Example: user says "can I hoard all the red gems" but Splendor rules say
"tokens" not "gems" in some editions. This gap cannot be bridged by
embeddings alone.
query_rewriter.py must:
1. Identify the game name from the query or session history
2. Translate colloquial phrasing to rule book terminology
3. Resolve coreferences from the last 3 turns
   ("What about nobles?" → resolve from prior context)
Use Claude Haiku — this is a simple reformulation task, not generation.
Conversation context budget: max 2000 tokens (truncate oldest turns first).
Token counting: use tiktoken cl100k_base as approximation for Claude tokenizer.

### Retrieval Pipeline (Two Stages)
Stage 1 — Hybrid Search: Client-side RRF produces top-20 candidates
  Dense: Pinecone cosine similarity (text-embedding-3-large) → top-20
  Sparse: Local BM25 (rank_bm25 library) → top-20
  Fusion: Reciprocal Rank Fusion (k=60, configurable in game_config)
  Output: top-20 unique chunks ranked by fused score

Stage 2 — Reranker: cross-encoder reranks top-20 → top-5
  Use cross-encoder/ms-marco-MiniLM-L-6-v2 (local, no API cost)
  Cross-encoder reads query+chunk together = much more accurate than
  bi-encoder embedding similarity alone
  Only pass top-5 to generation — reduces token cost significantly

### Context-Enriched Chunking
Every chunk must embed game name and section path in the text body:
"[Splendor - Noble Tiles] When a player reaches..."
Not just as metadata — hardcoded into the chunk text itself.
This improves both dense embedding recall and BM25 keyword matching.

### Tier Router Logic
Phase 1 implements Tier 1 and Tier 3 only. Binary decision.

Relevance score = sigmoid-normalized cross-encoder logit from reranker:
```
relevance_score = 1 / (1 + exp(-cross_encoder_logit))
```
Initial threshold: 0.85 (calibrate empirically in Start Instructions Step 8).
- relevance_score > threshold → Tier 1 (answer with citation)
- relevance_score <= threshold → Tier 3 (honest uncertainty)

Expected Phase 1 distribution: Tier 1 ~90%, Tier 3 ~10%.
(Tier 2 multi-hop at ~35% is a Phase 2 target after Chain-of-Retrieval.)

### Citation Verifier — Two-Step Process
After every Tier 1 generation, verify citations. Two steps:

Step 1 — String overlap check:
  For each cited claim in the answer, compute token overlap ratio
  between claim text and the cited chunk text.
  If overlap ratio > 0.6 → claim passes. Move to next claim.

Step 2 — LLM entailment check (only if Step 1 fails):
  For claims with overlap <= 0.6, make ONE Sonnet call with all
  remaining claims batched together.
  Prompt: "For each claim below, does the cited chunk support it?
  Return: [{claim, chunk_id, verdict: supported|unsupported|partial}]"

Cost budget: at most 1 extra Sonnet call per query (batched).

If any claim is unsupported → force downgrade to Tier 3.
The verifier reuses the top-5 chunks from generation — no separate
retrieval call.

To make this work, the generation prompt must instruct Sonnet to output
structured inline citations: each claim followed by [chunk_id].

### Tier 3 Output Format
Tier 3 is NOT a generation call. It returns a structured response:
- Top-3 retrieved chunks (if any), with relevance scores
- Explicit label: "The rule book does not address this directly"
- No LLM generation — just retrieved context presented as-is
(Community rulings from BGG deferred to Phase 2)

### Semantic Cache
- In-memory Python dict (key: query embedding, value: response)
- Brute-force cosine similarity against all cached embeddings
- Cache hit threshold: cosine similarity > 0.92
- Cache Tier 1 only. Never cache Tier 3.
- Session-scoped, does not persist across server restarts
- Note: every query still incurs one OpenAI embedding call (for cache
  lookup and retrieval). Cache saves Sonnet generation cost, not embedding cost.
- Expected <500 cached entries in Phase 1 — brute-force is fine.

### Conversation History
- Store last 3 turns per session
- Max 2000 tokens for conversation context (truncate oldest turns first)
- Token counting: tiktoken cl100k_base as Claude tokenizer approximation
- Query rewriter receives full history before rewriting
- Must perform coreference resolution before searching

### Structured Query Logging (SQLite)
Every query must log to logs/query_log.db:
  - timestamp
  - session_id
  - raw_query
  - rewritten_query
  - game_name
  - tier_decision (1 or 3)
  - top_chunks (JSON: chunk_id, score, text snippet)
  - final_answer (truncated to 500 chars)
  - latency_ms
  - cache_hit (bool)
Schema: logs/query_log.db, table: query_logs

### User Feedback Endpoint
POST /api/feedback with body: {session_id, query_id, helpful: bool, comment: str}
Store in logs/query_log.db, table: feedback
Keep it simple: thumbs up/down + optional comment.
Do NOT build feedback UI in Phase 1 — endpoint only.

### PDF Parser Strategy
Primary: LlamaParse API (accurate, handles complex layouts)
  - Free tier: 1000 pages/day (sufficient for Phase 1)
  - Mode: "cost_effective" for Splendor (simple layout)
Fallback trigger: LlamaParse API returns HTTP error (4xx/5xx),
  timeout > 30s, or rate limit exceeded → fall back to PyMuPDF.
ALWAYS check ingestion/cache/{game_name}_parsed.json first.
Never re-parse the same PDF twice.

### API Error Handling
Keep it minimal for MVP. No tenacity.
All external API calls (OpenAI, Anthropic, Pinecone, LlamaParse):
- Simple try/except with 1 retry on transient errors (timeout, 5xx)
- Clear error message on failure, logged to SQLite
- On failure after retry: return HTTP 503 with descriptive message

### Health Check
GET /health → {"status": "ok", "pinecone": bool, "bm25_loaded": bool}
Checks Pinecone connectivity and BM25 index loaded in memory.

## Game Config
```python
GAME_CONFIG = {
  "splendor": {
    "retrieval_hops": 1,
    "rerank_top_k": 5,
    "hybrid_top_k": 20,       # candidates per source before RRF
    "rrf_k": 60,              # RRF constant (higher = more weight to lower ranks)
    "multi_system_detection": False,
    "use_secondary_kb": False,
    "version_aware": False,
    "parser_mode": "cost_effective",
  },
  # Phase 2+
  "speakeasy": {
    "retrieval_hops": 2,
    "rerank_top_k": 5,
    "hybrid_top_k": 30,
    "rrf_k": 60,
    "multi_system_detection": False,
    "use_secondary_kb": True,
    "version_aware": True,
    "parser_mode": "agentic",
  },
  "fcm": {
    "retrieval_hops": 3,
    "rerank_top_k": 8,
    "hybrid_top_k": 40,
    "rrf_k": 60,
    "multi_system_detection": True,
    "use_secondary_kb": True,
    "version_aware": False,
    "parser_mode": "agentic",
  }
}
```

## Evaluation Pipeline

### Golden Dataset Format (splendor.json)
```json
{
  "query": "Can I take 2 gems of the same color on my turn?",
  "expected_tier": 1,
  "ground_truth": "You may take 2 gem tokens of the same color only if there are at least 4 tokens of that color available in the supply.",
  "expected_chunks": ["splendor_chunk_12", "splendor_chunk_13"],
  "required_chunk_keywords": ["same color", "4 tokens"],
  "forbidden_content": ["3 tokens", "any color"],
  "difficulty": "easy"
}
```
- `expected_chunks`: chunk IDs that should appear in retrieval top-5.
  Used to compute retrieval recall@5 separately from answer accuracy.
- `required_chunk_keywords`: at least one retrieved chunk must contain
  each keyword
- `forbidden_content`: final answer must NOT contain these phrases
- `difficulty`: easy | medium | hard — for stratified reporting

### eval_runner.py Reports
eval_runner.py produces two metric categories:
1. **Retrieval metrics**: recall@5 (do expected_chunks appear in top-5?),
   keyword hit rate (do required_chunk_keywords appear in retrieved chunks?)
2. **Answer metrics**: accuracy (answer matches ground_truth semantically),
   forbidden content check, tier correctness, hallucination count

This separation lets you diagnose whether failures come from retrieval
or generation. RAGAS adds LLM-as-judge metrics — deferred to Phase 2.

### Success Criteria Phase 1
- Tier 1 accuracy > 90% on golden dataset
- Top-5 retrieval recall > 85% (expected_chunks in top-5 after reranking)
- Zero hallucinations on golden dataset (verified by citation verifier)
- Tier 3 rate < 10% on golden dataset
- Semantic cache hit rate > 40% after 50 repeated/similar queries
- Query logging verified: every query has complete SQLite record
- /health endpoint returns 200

## Phase 1 KB Scope
kb_builder.py implements Primary KB only.
Secondary KB functions must be stubbed:
  raise NotImplementedError("Secondary KB not implemented until Phase 2")

## Continuous Practices (apply throughout all steps)
- After each Python file edit: ruff check . --fix
- After any test file change: pytest relevant test file
- Never commit with failing tests
- All code must have type annotations on function signatures
- Follow PEP 8 conventions

## Start Instructions
1. Set up project structure, pyproject.toml, .env.example, and install deps
   (include: sentence-transformers, rank-bm25, pinecone, openai, anthropic,
    llama-parse, pymupdf, fastapi, uvicorn, python-dotenv, tiktoken,
    ruff [dev], pytest [dev])
2. Place Splendor rulebook PDF in data/rulebooks/splendor.pdf
3. Write eval_runner.py + splendor.json golden dataset FIRST
   (Skeleton tests with expected interfaces. They will fail until the
    pipeline is wired — that is intentional.)
4. Implement ingestion: parse Splendor PDF → chunk → embed → upsert to
   Pinecone. Also generate BM25 pickle (ingestion/cache/splendor_bm25.pkl)
5. Run ingestion diagnostic to verify:
   - Chunk count and size distribution
   - Sample chunks look correct (game name embedded in text)
   - Pinecone upsert succeeded
   - BM25 pickle exists and chunk count matches Pinecone vector count
   Only proceed when ingestion looks clean.
6. Implement hybrid search (Pinecone dense + local BM25 + RRF) and verify
   retrieval in isolation: recall@5 > 85% on golden dataset queries
7. Add reranker: verify top-5 after reranking is better than top-5 before
8. **Calibrate tier router threshold**: run reranker on golden dataset,
   compute sigmoid scores, examine distribution, set threshold empirically.
   Document chosen threshold and justification.
9. Wire generation (Tier 1 answer + Tier 3 fallback) + citation verifier
10. Add query_logger.py: verify every query writes to SQLite
11. Add query rewriter (Haiku) + conversation history (last 3 turns, max 2000 tokens)
12. Add semantic cache (in-memory dict)
13. Add /api/feedback endpoint + /health endpoint
14. Run full eval against golden dataset. Iterate until all success criteria met.
15. Output PHASE1_COMPLETE.md with:
    - Accuracy metrics per difficulty level
    - Retrieval recall@5 metrics
    - Tier distribution on golden dataset
    - Calibrated threshold value and justification
    - Sample query log entries
    - Known limitations before Phase 2

## What NOT to Do in Phase 1
- No fine-tuning
- No LangGraph (plain function composition)
- No RAGAS (golden dataset eval only)
- No dynamic config routing
- No Tier 2 multi-hop implementation (stub only)
- No Tier 3 BGG community data
- No FCM or Speakeasy ingestion
- No Redis, SQLite cache, or FAISS (in-memory dict only for cache)
- No dedicated Pinecone paid features
- No Prometheus/Grafana monitoring (file logs + SQLite sufficient)
- No feedback UI (endpoint only)
- No agentic LlamaParse mode for Splendor
- No pinecone-text library (deprecated — use rank_bm25 instead)
- No tenacity (simple try/except with 1 retry)
