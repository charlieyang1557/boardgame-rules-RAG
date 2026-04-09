from __future__ import annotations

import os
import time
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="BoardGameOracle", version="0.1.0")

# ── Pydantic models ──────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    session_id: str | None = Field(None, max_length=64)
    game_name: str = Field(..., max_length=50)


class ChunkInfo(BaseModel):
    chunk_id: str
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    tier: int
    session_id: str
    query_id: int
    chunks: list[ChunkInfo]
    cache_hit: bool
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    games_loaded: list[str]


# ── Global state (initialized at startup) ────────────────────────────────────

_searchers: dict[str, object] = {}  # game_name -> HybridSearcher
_reranker = None
_cache = None
_session_manager = None
_logger = None
_anthropic_client = None
_openai_client = None


def _init_components() -> None:
    """Lazy-initialize all pipeline components (except per-game searchers)."""
    global _reranker, _cache, _session_manager, _logger
    global _anthropic_client, _openai_client

    if _logger is not None:
        return  # Already initialized

    from cache.semantic_cache import SemanticCache
    from conversation.session_manager import SessionManager
    from query_logging.query_logger import QueryLogger

    _logger = QueryLogger()
    _cache = SemanticCache()
    _session_manager = SessionManager()

    # API clients — may fail if keys not set (ok for health check)
    try:
        from anthropic import Anthropic
        from openai import OpenAI

        _anthropic_client = Anthropic()
        _openai_client = OpenAI()
    except Exception:
        pass

    # Reranker — may fail if model not downloaded
    try:
        from retrieval.reranker import Reranker

        _reranker = Reranker()
    except Exception:
        pass

    # Set up feedback router with logger
    from api.feedback import set_logger
    set_logger(_logger)


def _get_searcher(game_name: str):
    """Get or lazily initialize a HybridSearcher for the given game."""
    if game_name not in _searchers:
        bm25_path = f"ingestion/cache/{game_name}_bm25.pkl"
        if not os.path.exists(bm25_path):
            return None
        from retrieval.hybrid_search import HybridSearcher

        _searchers[game_name] = HybridSearcher(game_name=game_name, bm25_pickle_path=bm25_path)
    return _searchers[game_name]


def _embed_query(query: str) -> list[float]:
    """Embed a query using OpenAI text-embedding-3-large."""
    response = _openai_client.embeddings.create(
        model="text-embedding-3-large",
        input=query,
    )
    return response.data[0].embedding


def _run_pipeline(query: str, session_id: str, game_name: str) -> AskResponse:
    """Execute the full RAG pipeline."""
    _init_components()
    start = time.time()

    if _openai_client is None or _anthropic_client is None:
        raise HTTPException(status_code=503, detail="API clients not initialized. Check API keys in .env.")
    if _reranker is None:
        raise HTTPException(status_code=503, detail="Reranker model not loaded.")

    # Validate game_name against GAME_CONFIG
    from routing.game_config import GAME_CONFIG, get_config

    game_name = game_name.lower().strip()
    if game_name not in GAME_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown game: '{game_name}'. Supported: {list(GAME_CONFIG.keys())}")

    searcher = _get_searcher(game_name)
    if searcher is None:
        raise HTTPException(status_code=503, detail=f"BM25 index not loaded for '{game_name}'. Run ingestion first.")

    # 1. Session management
    history = _session_manager.get_history_text(session_id)

    # 2. Query rewriting with game-specific terminology map
    from retrieval.query_rewriter import rewrite_query
    from routing.game_config import get_terminology_map

    rewrite_result = rewrite_query(
        raw_query=query,
        history=history,
        anthropic_client=_anthropic_client,
        default_game=game_name,
        terminology_map=get_terminology_map(game_name),
    )
    rewritten = rewrite_result.rewritten_query
    resolved_game = game_name  # Trust the request, not the rewriter

    # 4. Embed rewritten query (used for cache lookup AND search)
    query_embedding = _embed_query(rewritten)

    # 5. Check semantic cache (keyed on game + rewritten query embedding)
    cached = _cache.lookup(query_embedding, game_name=resolved_game)
    if cached is not None:
        latency = (time.time() - start) * 1000
        query_id = _logger.log_query(
            session_id=session_id,
            raw_query=query,
            rewritten_query=rewritten,
            game_name=resolved_game,
            tier_decision=cached["tier"],
            top_chunks=[],
            final_answer=cached["answer"],
            latency_ms=latency,
            cache_hit=True,
        )
        _session_manager.add_turn(session_id, query, cached["answer"])
        return AskResponse(
            answer=cached["answer"],
            tier=cached["tier"],
            session_id=session_id,
            query_id=query_id,
            chunks=[],
            cache_hit=True,
            latency_ms=latency,
        )
    # 6. Hybrid search
    config = get_config(resolved_game)
    search_results = searcher.search(
        query=rewritten,
        query_embedding=query_embedding,
        top_k=config.hybrid_top_k,
        rrf_k=config.rrf_k,
    )

    # 6. Rerank (with location-aware promotion for games with defined locations)
    from routing.game_config import get_location_names

    location_names = get_location_names(resolved_game)
    chunks_for_rerank = [
        {"chunk_id": r.chunk_id, "text": r.text} for r in search_results
    ]
    reranked = _reranker.rerank(
        rewritten, chunks_for_rerank, top_k=config.rerank_top_k,
        alt_query=query, location_names=location_names,
    )

    # 7. Tier routing
    from routing.tier_router import route_tier

    best_score = reranked[0].raw_score if reranked else -10.0
    tier_decision = route_tier(
        best_score,
        threshold=config.tier1_threshold,
        tier2_threshold=config.tier2_threshold if config.retrieval_hops > 1 else None,
    )

    # Override: if a location-promoted chunk is #1, force Tier 1
    if location_names and reranked:
        query_lower = query.lower()
        matched_loc = [loc for loc in location_names if loc.lower() in query_lower]
        if matched_loc and any(loc.lower() in reranked[0].text.lower() for loc in matched_loc):
            if tier_decision.tier in (2, 3):
                tier_decision = route_tier(10.0)  # Force Tier 1

    # 8. Generation
    from generation.generator import generate_tier1, generate_tier3
    from verification.citation_verifier import verify_citations

    top_chunks = [
        {"chunk_id": r.chunk_id, "text": r.text, "sigmoid_score": r.sigmoid_score}
        for r in reranked
    ]

    if tier_decision.tier == 1:
        gen_result = generate_tier1(rewritten, top_chunks, _anthropic_client)
        verification = verify_citations(gen_result.answer, top_chunks, _anthropic_client)
        if not verification.all_supported:
            # Escalate to Tier 2 if game supports multi-hop, else Tier 3
            if config.retrieval_hops > 1:
                tier_decision = route_tier(0.0, threshold=1.0, tier2_threshold=0.0)  # Force Tier 2
            else:
                gen_result = generate_tier3(
                    top_chunks, anthropic_client=_anthropic_client, query=rewritten,
                )

    elif tier_decision.tier == 2:
        # Tier 2: Chain-of-Retrieval multi-hop
        from retrieval.multi_hop import ChainOfRetrieval

        chain = ChainOfRetrieval(
            searcher=searcher, reranker=_reranker,
            anthropic_client=_anthropic_client, openai_client=_openai_client,
            max_hops=min(config.retrieval_hops, 2),
        )
        chain_result = chain.retrieve_and_reason(
            query=rewritten, game_name=resolved_game, config=config,
            alt_query=query, location_names=location_names,
            initial_chunks=top_chunks,
        )

        if chain_result.is_answerable:
            # Parse citations from chain answer
            import re as _re
            citation_pattern = _re.compile(r'\[([^\]]+)\]')
            found_ids = citation_pattern.findall(chain_result.answer)
            valid_ids = {c["chunk_id"] for c in chain_result.merged_chunks}

            from generation.generator import GenerationResult
            gen_result = GenerationResult(
                answer=chain_result.answer,
                citations=[{"claim": "", "chunk_id": cid} for cid in found_ids if cid in valid_ids],
                tier=2,
            )
            # Verify citations on merged chunks
            verification = verify_citations(gen_result.answer, chain_result.merged_chunks, _anthropic_client)
            if not verification.all_supported:
                gen_result = generate_tier3(
                    chain_result.merged_chunks, anthropic_client=_anthropic_client, query=rewritten,
                )
            else:
                top_chunks = chain_result.merged_chunks  # Update for logging
        else:
            gen_result = generate_tier3(
                top_chunks, anthropic_client=_anthropic_client, query=rewritten,
            )

    else:
        gen_result = generate_tier3(
            top_chunks, anthropic_client=_anthropic_client, query=rewritten,
        )

    # 10. Cache (Tier 1 only, keyed on game + rewritten query embedding)
    _cache.store(
        query_embedding,
        {"answer": gen_result.answer, "tier": gen_result.tier},
        gen_result.tier,
        game_name=resolved_game,
    )

    # 11. Log
    latency = (time.time() - start) * 1000
    chunk_log = [{"chunk_id": r.chunk_id, "score": r.sigmoid_score, "text": r.text[:200]} for r in reranked]
    query_id = _logger.log_query(
        session_id=session_id,
        raw_query=query,
        rewritten_query=rewritten,
        game_name=resolved_game,
        tier_decision=gen_result.tier,
        top_chunks=chunk_log,
        final_answer=gen_result.answer,
        latency_ms=latency,
        cache_hit=False,
    )

    # 12. Update session
    _session_manager.add_turn(session_id, query, gen_result.answer)

    return AskResponse(
        answer=gen_result.answer,
        tier=gen_result.tier,
        session_id=session_id,
        query_id=query_id,
        chunks=[ChunkInfo(chunk_id=r.chunk_id, text=r.text[:300], score=r.sigmoid_score) for r in reranked],
        cache_hit=False,
        latency_ms=latency,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    _init_components()
    # Check which games have BM25 indexes available
    from routing.game_config import GAME_CONFIG

    loaded = [g for g in GAME_CONFIG if _get_searcher(g) is not None]
    return HealthResponse(
        status="ok",
        games_loaded=loaded,
    )


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    import logging

    logger = logging.getLogger(__name__)
    session_id = request.session_id or str(uuid.uuid4())
    try:
        return _run_pipeline(request.query, session_id, request.game_name)
    except HTTPException:
        raise
    except (TimeoutError, ConnectionError, OSError) as e:
        # Retry once on transient network errors only
        logger.warning("Transient error, retrying: %s", e)
        try:
            return _run_pipeline(request.query, session_id, request.game_name)
        except Exception:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.exception("Pipeline error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Include feedback router ──────────────────────────────────────────────────

from api.feedback import router as feedback_router  # noqa: E402

app.include_router(feedback_router)

# ── Serve React frontend (must come AFTER all API routes) ───────────────────

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(_frontend_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    _assets_dir = os.path.join(_frontend_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="static-assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str) -> FileResponse:
        """Serve React SPA — all non-API routes return index.html."""
        file_path = os.path.join(_frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_frontend_dir, "index.html"))
