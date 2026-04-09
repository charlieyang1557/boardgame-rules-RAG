# BoardGameOracle

A RAG-based Q&A system that answers board game rules questions with citations, multi-hop reasoning, and honest uncertainty handling.

Ask a question in plain language, get an answer backed by the actual rule book — with page references you can verify.

## Supported Games

| Game | Complexity | Multi-hop |
|------|-----------|-----------|
| **Splendor** | Simple | Single-hop |
| **Catan** | Simple | Single-hop |
| **Speakeasy** | Medium | 2-hop |
| **Food Chain Magnate** | Complex | 3-hop |

## How It Works

```
User Question
     |
     v
Query Rewriter (Claude Haiku)
  - Translates colloquial phrasing to rule book terminology
  - Resolves coreferences from conversation history
     |
     v
Hybrid Search (Pinecone dense + BM25 sparse + RRF fusion)
  - Top-20 candidates from each source
  - Reciprocal Rank Fusion merges results
     |
     v
Cross-Encoder Reranker (local, no API cost)
  - Reranks top-20 → top-5 (or top-8 for FCM)
     |
     v
Tier Router
  - Tier 1: Direct answer with citations
  - Tier 2: Multi-hop chain-of-retrieval (iterative search)
  - Tier 3: Honest uncertainty — returns raw chunks, no generation
     |
     v
Citation Verifier
  - String overlap check → LLM entailment fallback
  - Unsupported claims → downgrade to Tier 3
     |
     v
Answer with inline citations + expandable source cards
```

## Live Demo

Deployed on Railway: https://boardgame-rules-rag-production.up.railway.app

## Screenshots

The frontend uses a warm "Tabletop Oracle" aesthetic — parchment tones, serif headings (Crimson Pro), jewel-tone tier badges.

- **Tier 1** (green): Direct answer with high confidence
- **Tier 2** (amber): Synthesized from multiple rules
- **Tier 3** (orange): Uncertain — shows relevant chunks without generating an answer

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- API keys: Pinecone, OpenAI, Anthropic, LlamaParse

### Setup

```bash
# Clone
git clone https://github.com/charlieyang1557/boardgame-rules-RAG.git
cd boardgame-rules-RAG

# Python deps
pip install -e ".[dev]"

# Frontend deps
cd frontend && npm install && cd ..

# Environment
cp .env.example .env
# Fill in your API keys
```

### Run Locally

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Start server (serves both API + frontend)
uvicorn api.main:app --port 8000
```

Open http://localhost:8000

### Run Tests

```bash
# Backend tests
python -m pytest tests/ -q

# Frontend tests
cd frontend && npx vitest run
```

## Tech Stack

### Backend
- **Vector DB**: Pinecone serverless (free tier, dense vectors)
- **Sparse Search**: Client-side BM25 via rank_bm25
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2 (local)
- **Embeddings**: OpenAI text-embedding-3-large (3072 dims)
- **LLM**: Claude Haiku (query rewriting) + Claude Sonnet (generation + verification)
- **PDF Parsing**: LlamaParse (primary), PyMuPDF (fallback)
- **Framework**: FastAPI
- **Logging**: SQLite

### Frontend
- React 18 + TypeScript
- Tailwind CSS v4
- Vite

### Deployment
- Single-service Docker container (FastAPI serves React build via StaticFiles)
- Railway (Hobby plan)

## Project Structure

```
boardgame-rules-RAG/
├── api/                    # FastAPI endpoints (/ask, /health, /api/feedback)
├── ingestion/              # PDF parsing, chunking, KB building
├── retrieval/              # Hybrid search, reranker, query rewriter, multi-hop
├── routing/                # Tier router, game config
├── generation/             # Tier 1 answer + Tier 3 fallback
├── verification/           # Citation verifier (string overlap + LLM entailment)
├── cache/                  # Semantic cache (in-memory, cosine similarity)
├── conversation/           # Session manager (last 3 turns, 2000 token budget)
├── query_logging/          # SQLite structured logging
├── evaluation/             # Golden dataset + eval runner
├── frontend/               # React chat UI
├── tests/                  # pytest suite
└── Dockerfile              # Multi-stage build (Node + Python)
```

## Evaluation Results

| Game | Accuracy | Retrieval Recall@5 |
|------|----------|-------------------|
| Splendor | 91% | > 85% |
| Catan | 91% | > 85% |
| Speakeasy | 82% | > 80% |
| FCM | 79% | > 75% |

FCM's Tier 2 (multi-hop) accuracy: **90%** — well above the 65% target.

## License

MIT
