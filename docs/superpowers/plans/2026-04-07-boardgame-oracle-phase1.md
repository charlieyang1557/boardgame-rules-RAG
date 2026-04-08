# BoardGameOracle Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a RAG-based Q&A system for Splendor board game rules with hybrid retrieval, citation verification, and honest uncertainty handling.

**Architecture:** Linear pipeline — rewrite → hybrid search (Pinecone dense + local BM25 + RRF) → cross-encoder rerank → tier route → generate with citations → verify → log. No graph framework; plain Python function composition. FastAPI serves the API.

**Tech Stack:** Pinecone (dense), rank_bm25 (sparse), sentence-transformers CrossEncoder (reranker), OpenAI text-embedding-3-large, Claude Haiku (rewrite), Claude Sonnet (generation), LlamaParse + PyMuPDF (PDF), FastAPI, SQLite (logging), pytest.

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Dependencies and project metadata |
| `.env.example` | API key template |
| `.gitignore` | Ignore logs/, .env, cache/, __pycache__ |
| `ingestion/pdf_parser.py` | LlamaParse primary, PyMuPDF fallback, cache to JSON |
| `ingestion/chunker.py` | Split parsed text → context-enriched chunks |
| `ingestion/kb_builder.py` | Embed chunks → upsert Pinecone + build BM25 pickle |
| `retrieval/hybrid_search.py` | Pinecone dense top-20 + BM25 top-20 + RRF → top-20 |
| `retrieval/reranker.py` | CrossEncoder rerank top-20 → top-5 with sigmoid scores |
| `retrieval/query_rewriter.py` | Haiku-based rewrite + coref resolution |
| `routing/game_config.py` | GAME_CONFIG dict |
| `routing/tier_router.py` | Binary Tier 1/3 decision on sigmoid score |
| `generation/generator.py` | Tier 1 cited answer + Tier 3 structured fallback |
| `verification/citation_verifier.py` | String overlap + batched Sonnet entailment |
| `cache/semantic_cache.py` | In-memory dict, brute-force cosine, threshold 0.92 |
| `conversation/session_manager.py` | Last 3 turns, max 2000 tokens, tiktoken counting |
| `query_logging/query_logger.py` | SQLite structured logging |
| `evaluation/golden_dataset/splendor.json` | Golden Q&A pairs for Splendor |
| `evaluation/eval_runner.py` | Retrieval recall@5 + answer accuracy regression |
| `api/main.py` | FastAPI app, /ask endpoint, /health |
| `api/feedback.py` | POST /api/feedback endpoint |

## Dependency Graph

```
Task 1 (Scaffolding)
  ├─→ Task 2 (Golden Dataset + Eval Runner) ──────────────────┐
  ├─→ Task 3 (Game Config + Tier Router)                      │
  ├─→ Task 4 (Query Logging — SQLite)                         │
  └─→ Task 5 (Ingestion Pipeline)                             │
        └─→ Task 6 (Hybrid Search + Reranker)                 │
              ├─→ Task 7 (Generation + Citation Verifier)      │
              ├─→ Task 8 (Query Rewriter + Conversation)       │
              └─→ Task 9 (Semantic Cache)                      │
                    └─→ Task 10 (FastAPI Layer) ←──────────────┘
                          └─→ Task 11 (Wire + Full Eval)
```

Tasks 2, 3, 4, 5 are independent after Task 1.
Tasks 8, 9 are independent after Task 6.

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`, `.env.example`, `.gitignore`
- Create: all `__init__.py` files, `data/rulebooks/` directory
- Symlink: `ba-splendor-rulebook.pdf` → `data/rulebooks/splendor.pdf`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "boardgame-oracle"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40.0",
    "openai>=1.50.0",
    "pinecone>=5.0.0",
    "rank-bm25>=0.2.2",
    "sentence-transformers>=3.0.0",
    "tiktoken>=0.7.0",
    "llama-parse>=0.5.0",
    "pymupdf>=1.24.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "python-dotenv>=1.0.0",
    "numpy>=1.26.0",
]

[project.optional-dependencies]
dev = ["ruff>=0.6.0", "pytest>=8.0.0", "pytest-asyncio>=0.24.0", "httpx>=0.27.0"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests", "evaluation"]
```

- [ ] **Step 2: Create .env.example**

```
PINECONE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLAMA_CLOUD_API_KEY=
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
logs/
ingestion/cache/
*.pkl
.venv/
dist/
*.egg-info/
```

- [ ] **Step 4: Create directory structure with __init__.py files**

Create directories: `data/rulebooks/`, `ingestion/cache/`, `retrieval/`, `routing/`, `generation/`, `verification/`, `cache/`, `conversation/`, `query_logging/`, `evaluation/golden_dataset/`, `api/`, `logs/`, `tests/`

Create empty `__init__.py` in: ingestion, retrieval, routing, generation, verification, cache, conversation, query_logging, evaluation, api.

- [ ] **Step 5: Symlink Splendor rulebook**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
ln -s ../../ba-splendor-rulebook.pdf data/rulebooks/splendor.pdf
```

- [ ] **Step 6: Initialize git and install deps**

```bash
git init
pip install -e ".[dev]"
git add -A && git commit -m "chore: initial project scaffolding"
```

---

### Task 2: Golden Dataset + Eval Runner

**Files:**
- Create: `evaluation/golden_dataset/splendor.json`
- Create: `evaluation/eval_runner.py`
- Test: `pytest evaluation/eval_runner.py -v`

- [ ] **Step 1: Write splendor.json golden dataset**

30 questions covering: gem taking, reserving cards, noble tiles, development cards, gold tokens, winning conditions, turn structure, edge cases. Each entry has query, expected_tier, ground_truth, expected_chunks (placeholder IDs until ingestion), required_chunk_keywords, forbidden_content, difficulty.

- [ ] **Step 2: Write eval_runner.py skeleton**

Functions:
- `load_golden_dataset(path: str) -> list[dict]`
- `evaluate_retrieval(query: str, retrieved_chunks: list, expected: dict) -> dict` — computes recall@5, keyword hit rate
- `evaluate_answer(answer: str, expected: dict) -> dict` — accuracy, forbidden content, tier correctness
- `run_full_eval(pipeline_fn, dataset_path: str) -> dict` — runs pipeline on all questions, aggregates metrics
- `print_report(results: dict) -> None` — prints stratified report by difficulty

Skeleton tests that assert function signatures exist but skip actual pipeline calls.

- [ ] **Step 3: Run eval skeleton tests**

Run: `pytest evaluation/eval_runner.py -v`
Expected: tests pass (skeleton only, no pipeline dependency)

- [ ] **Step 4: Commit**

```bash
git add evaluation/ && git commit -m "feat: golden dataset and eval runner skeleton"
```

---

### Task 3: Game Config + Tier Router

**Files:**
- Create: `routing/game_config.py`
- Create: `routing/tier_router.py`
- Create: `tests/test_tier_router.py`

- [ ] **Step 1: Write game_config.py**

GAME_CONFIG dict exactly as specified in CLAUDE.md. Helper function: `get_config(game_name: str) -> dict`.

- [ ] **Step 2: Write failing test for tier_router**

```python
import math
from routing.tier_router import route_tier

def test_tier1_high_score():
    result = route_tier(cross_encoder_logit=2.0, threshold=0.85)
    assert result.tier == 1
    assert result.relevance_score > 0.85

def test_tier3_low_score():
    result = route_tier(cross_encoder_logit=-1.0, threshold=0.85)
    assert result.tier == 3
    assert result.relevance_score <= 0.85

def test_sigmoid_correctness():
    result = route_tier(cross_encoder_logit=0.0, threshold=0.85)
    assert abs(result.relevance_score - 0.5) < 0.01
```

- [ ] **Step 3: Implement tier_router.py**

```python
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class TierDecision:
    tier: int
    relevance_score: float

def route_tier(cross_encoder_logit: float, threshold: float = 0.85) -> TierDecision:
    score = 1.0 / (1.0 + math.exp(-cross_encoder_logit))
    tier = 1 if score > threshold else 3
    return TierDecision(tier=tier, relevance_score=score)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_tier_router.py -v`

- [ ] **Step 5: Commit**

```bash
git add routing/ tests/test_tier_router.py && git commit -m "feat: game config and tier router with sigmoid scoring"
```

---

### Task 4: Query Logging (SQLite)

**Files:**
- Create: `query_logging/query_logger.py`
- Create: `tests/test_query_logger.py`

- [ ] **Step 1: Write failing tests**

Test that: init creates table, log_query inserts a row, log_feedback inserts to feedback table, all fields are stored correctly, timestamps are ISO format.

- [ ] **Step 2: Implement query_logger.py**

```python
class QueryLogger:
    def __init__(self, db_path: str = "logs/query_log.db"):
        # Create tables: query_logs, feedback
    def log_query(self, session_id, raw_query, rewritten_query, game_name,
                  tier_decision, top_chunks, final_answer, latency_ms, cache_hit) -> int:
        # Insert row, return query_id
    def log_feedback(self, session_id, query_id, helpful, comment) -> None:
        # Insert feedback row
```

- [ ] **Step 3: Run tests, verify pass**
- [ ] **Step 4: Commit**

---

### Task 5: Ingestion Pipeline

**Files:**
- Create: `ingestion/pdf_parser.py`
- Create: `ingestion/chunker.py`
- Create: `ingestion/kb_builder.py`
- Create: `tests/test_chunker.py`

- [ ] **Step 1: Write pdf_parser.py**

```python
def parse_pdf(pdf_path: str, game_name: str, mode: str = "cost_effective") -> list[dict]:
    cache_path = f"ingestion/cache/{game_name}_parsed.json"
    # Check cache first
    # Try LlamaParse, fallback to PyMuPDF on error/timeout
    # Save to cache
    # Return list of {page: int, text: str, section: str}
```

- [ ] **Step 2: Write failing tests for chunker**

Test context-enriched prefix, chunk size bounds (200-600 tokens), overlap, game name in every chunk.

- [ ] **Step 3: Implement chunker.py**

```python
def chunk_parsed_pages(pages: list[dict], game_name: str,
                       chunk_size: int = 400, overlap: int = 50) -> list[dict]:
    # For each page, split text into chunks
    # Prepend "[{game_name} - {section}] " to each chunk
    # Return list of {chunk_id, text, game_name, section, page}
```

- [ ] **Step 4: Run chunker tests, verify pass**

- [ ] **Step 5: Implement kb_builder.py**

```python
def build_primary_kb(game_name: str, pdf_path: str) -> dict:
    # Parse PDF → chunk → embed via OpenAI → upsert to Pinecone
    # Build BM25 index → pickle to ingestion/cache/{game_name}_bm25.pkl
    # Return stats: {chunk_count, pinecone_count, bm25_count}

def build_secondary_kb(game_name: str) -> None:
    raise NotImplementedError("Secondary KB not implemented until Phase 2")
```

- [ ] **Step 6: Run ingestion on Splendor PDF**

```bash
python -c "from ingestion.kb_builder import build_primary_kb; print(build_primary_kb('splendor', 'data/rulebooks/splendor.pdf'))"
```

Verify: chunk_count > 0, all three counts match, sample chunk has "[Splendor -" prefix.

- [ ] **Step 7: Commit**

```bash
git add ingestion/ tests/test_chunker.py && git commit -m "feat: ingestion pipeline with LlamaParse, chunker, and Pinecone upsert"
```

---

### Task 6: Hybrid Search + Reranker

**Files:**
- Create: `retrieval/hybrid_search.py`
- Create: `retrieval/reranker.py`
- Create: `tests/test_hybrid_search.py`
- Create: `tests/test_reranker.py`

- [ ] **Step 1: Write failing tests for hybrid_search**

Test RRF fusion logic with mock ranked lists. Test that top-20 output contains chunks from both sources.

- [ ] **Step 2: Implement hybrid_search.py**

```python
class HybridSearcher:
    def __init__(self, game_name: str, pinecone_index, bm25_pickle_path: str):
        # Load BM25 from pickle
        # Validate chunk count vs Pinecone namespace

    def search(self, query: str, query_embedding: list[float],
               top_k: int = 20, rrf_k: int = 60) -> list[dict]:
        # 1. Pinecone dense search → top_k results
        # 2. BM25 search → top_k results
        # 3. RRF fusion → top_k by fused score
        # Return [{chunk_id, text, score, source}]
```

- [ ] **Step 3: Run hybrid_search tests, verify pass**

- [ ] **Step 4: Write failing tests for reranker**

Test that reranker output has sigmoid scores, output length <= input length, sorted descending.

- [ ] **Step 5: Implement reranker.py**

```python
class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
        # Score each (query, chunk.text) pair
        # Apply sigmoid to logits
        # Sort descending, return top_k
```

- [ ] **Step 6: Run reranker tests, verify pass**

- [ ] **Step 7: Integration test — run hybrid search + rerank on golden dataset queries**

Verify retrieval recall@5 > 85%.

- [ ] **Step 8: Commit**

```bash
git add retrieval/ tests/test_hybrid_search.py tests/test_reranker.py && git commit -m "feat: hybrid search (Pinecone + BM25 + RRF) and cross-encoder reranker"
```

---

### Task 7: Generation + Citation Verifier

**Files:**
- Create: `generation/generator.py`
- Create: `verification/citation_verifier.py`
- Create: `tests/test_generator.py`
- Create: `tests/test_citation_verifier.py`

- [ ] **Step 1: Write failing tests for citation_verifier**

Test string overlap calculation, test that unsupported claims trigger Tier 3, test batched entailment prompt format.

- [ ] **Step 2: Implement citation_verifier.py**

```python
def compute_token_overlap(claim: str, chunk_text: str) -> float:
    # Tokenize both, compute |intersection| / |claim_tokens|

def verify_citations(answer: str, chunks: list[dict],
                     anthropic_client) -> VerificationResult:
    # Parse inline citations [chunk_id] from answer
    # Step 1: string overlap > 0.6 = pass
    # Step 2: batch remaining claims into ONE Sonnet call
    # Return VerificationResult(all_supported: bool, details: list)
```

- [ ] **Step 3: Run citation verifier tests, verify pass**

- [ ] **Step 4: Write failing tests for generator**

Test Tier 1 output has citations, Tier 3 output has "does not address" label, Tier 3 has no LLM call.

- [ ] **Step 5: Implement generator.py**

```python
def generate_tier1(query: str, chunks: list[dict],
                   anthropic_client) -> GenerationResult:
    # Sonnet call with system prompt requiring inline [chunk_id] citations
    # Return GenerationResult(answer, citations, tier=1)

def generate_tier3(chunks: list[dict]) -> GenerationResult:
    # No LLM call — structured response from top-3 chunks
    # Return GenerationResult(answer, citations=[], tier=3)
```

- [ ] **Step 6: Run generator tests, verify pass**
- [ ] **Step 7: Commit**

---

### Task 8: Query Rewriter + Conversation History

**Files:**
- Create: `retrieval/query_rewriter.py`
- Create: `conversation/session_manager.py`
- Create: `tests/test_session_manager.py`
- Create: `tests/test_query_rewriter.py`

- [ ] **Step 1: Write failing tests for session_manager**

Test: add turns, max 3 turns stored, token budget truncation (2000 tokens), oldest turn dropped first.

- [ ] **Step 2: Implement session_manager.py**

```python
class SessionManager:
    def __init__(self, max_turns: int = 3, max_tokens: int = 2000):
        self.sessions: dict[str, list[dict]] = {}

    def add_turn(self, session_id: str, query: str, answer: str) -> None:
    def get_history(self, session_id: str) -> list[dict]:
    def get_history_text(self, session_id: str) -> str:
        # Truncate to max_tokens using tiktoken cl100k_base
```

- [ ] **Step 3: Run session_manager tests, verify pass**

- [ ] **Step 4: Write failing tests for query_rewriter**

Test: game name extraction, coreference resolution with history, output is rewritten query string.

- [ ] **Step 5: Implement query_rewriter.py**

```python
def rewrite_query(raw_query: str, history: str,
                  anthropic_client) -> RewriteResult:
    # Claude Haiku call
    # System prompt: identify game, translate colloquial → formal, resolve coref
    # Return RewriteResult(rewritten_query, game_name)
```

- [ ] **Step 6: Run query_rewriter tests, verify pass**
- [ ] **Step 7: Commit**

---

### Task 9: Semantic Cache

**Files:**
- Create: `cache/semantic_cache.py`
- Create: `tests/test_semantic_cache.py`

- [ ] **Step 1: Write failing tests**

Test: cache miss on empty, cache hit on identical embedding, cache miss below 0.92, only Tier 1 cached, Tier 3 rejected.

- [ ] **Step 2: Implement semantic_cache.py**

```python
class SemanticCache:
    def __init__(self, threshold: float = 0.92):
        self.embeddings: list[list[float]] = []
        self.responses: list[dict] = []

    def lookup(self, query_embedding: list[float]) -> dict | None:
        # Brute-force cosine sim against all cached embeddings
        # Return response if max_sim > threshold, else None

    def store(self, query_embedding: list[float], response: dict, tier: int) -> None:
        # Only cache if tier == 1
```

- [ ] **Step 3: Run tests, verify pass**
- [ ] **Step 4: Commit**

---

### Task 10: FastAPI Layer

**Files:**
- Create: `api/main.py`
- Create: `api/feedback.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing tests for API endpoints**

Test /health returns 200, /ask returns structured response, /api/feedback stores to SQLite.

- [ ] **Step 2: Implement main.py**

```python
app = FastAPI(title="BoardGameOracle")

@app.get("/health")
async def health():
    # Check Pinecone + BM25 loaded

@app.post("/ask")
async def ask(request: AskRequest):
    # Full pipeline: rewrite → search → rerank → route → generate → verify → log
    # Check cache first
```

- [ ] **Step 3: Implement feedback.py**

```python
router = APIRouter()

@router.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    # Store in SQLite via QueryLogger
```

- [ ] **Step 4: Run API tests, verify pass**
- [ ] **Step 5: Commit**

---

### Task 11: Wire Pipeline + Full Eval

- [ ] **Step 1: Create pipeline orchestrator function**

Wire all components into `run_pipeline(query, session_id)` that executes the full linear flow.

- [ ] **Step 2: Update golden dataset expected_chunks with real chunk IDs from ingestion**

- [ ] **Step 3: Run eval_runner.py against full pipeline**

Iterate until: accuracy > 90%, recall@5 > 85%, zero hallucinations, Tier 3 < 10%.

- [ ] **Step 4: Calibrate tier router threshold**

Run reranker on all golden queries, plot sigmoid score distribution, adjust threshold.

- [ ] **Step 5: Test semantic cache hit rate**

Run 50 queries including repeats/paraphrases. Verify cache hit > 40%.

- [ ] **Step 6: Verify query logging completeness**

Check every golden dataset query has a complete SQLite record.

- [ ] **Step 7: Write PHASE1_COMPLETE.md**

- [ ] **Step 8: Final commit**

```bash
git add -A && git commit -m "feat: Phase 1 complete — Splendor RAG pipeline"
```
