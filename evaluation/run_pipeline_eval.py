"""Run the real RAG pipeline over a golden dataset and report metrics.

Mirrors api/main._run_pipeline's retrieval -> rerank -> route -> generate ->
verify path, but skips the semantic cache, query log, and session manager so
the evaluation has no side effects and always exposes the reranker score.

Usage:
    python -m evaluation.run_pipeline_eval <game> [--lang en|zh] [--calibrate]

Requires live API keys in .env (OpenAI, Anthropic, Pinecone).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PipelineOutput:
    answer: str
    tier: int
    retrieved_chunks: list[dict]
    best_sigmoid: float


def build_pipeline_fn(game_name: str, language: str = "en"):
    """Build a callable query -> PipelineOutput using the production modules."""
    from anthropic import Anthropic
    from openai import OpenAI

    from generation.generator import generate_tier1, generate_tier3
    from retrieval.hybrid_search import HybridSearcher
    from retrieval.query_rewriter import rewrite_query
    from retrieval.reranker import Reranker
    from routing.game_config import (
        get_config,
        get_location_names,
        get_terminology_map,
    )
    from routing.tier_router import route_tier
    from verification.citation_verifier import verify_citations

    anthropic_client = Anthropic()
    openai_client = OpenAI()
    reranker = Reranker()
    searcher = HybridSearcher(
        game_name=game_name,
        bm25_pickle_path=f"ingestion/cache/{game_name}_bm25.pkl",
    )
    config = get_config(game_name)
    term = get_terminology_map(game_name)
    loc = get_location_names(game_name)

    # Optional translation (language feature); import lazily so the tool works
    # even before the translator module exists.
    try:
        from generation.translator import translate_answer
    except Exception:  # pragma: no cover
        def translate_answer(answer, target_lang, client):  # type: ignore
            return answer

    def run(query: str) -> dict:
        rewritten = rewrite_query(
            query, "", anthropic_client, default_game=game_name, terminology_map=term
        ).rewritten_query
        emb = openai_client.embeddings.create(
            model="text-embedding-3-large", input=rewritten
        ).data[0].embedding
        results = searcher.search(
            query=rewritten, query_embedding=emb,
            top_k=config.hybrid_top_k, rrf_k=config.rrf_k,
        )
        reranked = reranker.rerank(
            rewritten, [{"chunk_id": r.chunk_id, "text": r.text} for r in results],
            top_k=config.rerank_top_k, alt_query=query, location_names=loc,
        )
        best_raw = reranked[0].raw_score if reranked else -10.0
        best_sigmoid = reranked[0].sigmoid_score if reranked else 0.0
        tier_decision = route_tier(
            best_raw, threshold=config.tier1_threshold,
            tier2_threshold=config.tier2_threshold if config.retrieval_hops > 1 else None,
        )
        top_chunks = [
            {"chunk_id": r.chunk_id, "text": r.text, "sigmoid_score": r.sigmoid_score}
            for r in reranked
        ]

        if tier_decision.tier == 1:
            gen = generate_tier1(rewritten, top_chunks, anthropic_client)
            verification = verify_citations(gen.answer, top_chunks, anthropic_client)
            if not verification.all_supported:
                gen = generate_tier3(
                    top_chunks, anthropic_client=anthropic_client,
                    query=rewritten, language=language,
                )
        elif tier_decision.tier == 2:
            from retrieval.multi_hop import ChainOfRetrieval
            from generation.generator import GenerationResult
            chain = ChainOfRetrieval(
                searcher=searcher, reranker=reranker,
                anthropic_client=anthropic_client, openai_client=openai_client,
                max_hops=min(config.retrieval_hops, 2),
            )
            cr = chain.retrieve_and_reason(
                query=rewritten, game_name=game_name, config=config,
                alt_query=query, location_names=loc, initial_chunks=top_chunks,
            )
            if cr.is_answerable:
                gen = GenerationResult(answer=cr.answer, citations=[], tier=2)
                v = verify_citations(gen.answer, cr.merged_chunks, anthropic_client)
                if not v.all_supported:
                    gen = generate_tier3(
                        cr.merged_chunks, anthropic_client=anthropic_client,
                        query=rewritten, language=language,
                    )
                else:
                    top_chunks = cr.merged_chunks
            else:
                gen = generate_tier3(
                    top_chunks, anthropic_client=anthropic_client,
                    query=rewritten, language=language,
                )
        else:
            gen = generate_tier3(
                top_chunks, anthropic_client=anthropic_client,
                query=rewritten, language=language,
            )

        # Mirror production: Tier 3 is already localized by generate_tier3;
        # only official Tier 1/2 answers are translated (verify-then-translate).
        answer = gen.answer
        if language != "en" and gen.tier in (1, 2):
            answer = translate_answer(answer, language, anthropic_client)

        return {
            "answer": answer,
            "tier": gen.tier,
            "retrieved_chunks": [{"id": c["chunk_id"], "text": c["text"]} for c in top_chunks],
            "best_sigmoid": best_sigmoid,
        }

    return run


def main() -> None:
    from evaluation.eval_runner import (
        evaluate_answer,
        evaluate_retrieval,
        load_golden_dataset,
        EvalReport,
        EvalResult,
        print_report,
    )

    args = sys.argv[1:]
    game = args[0] if args else "splendor"
    language = "en"
    calibrate = "--calibrate" in args
    if "--lang" in args:
        idx = args.index("--lang")
        raw = args[idx + 1] if idx + 1 < len(args) else "en"
        language = raw if raw in {"en", "zh"} else "en"

    dataset_path = f"evaluation/golden_dataset/{game}.json"
    dataset = load_golden_dataset(dataset_path)
    run = build_pipeline_fn(game, language=language)

    results: list[EvalResult] = []
    calib: list[tuple[float, int, int]] = []  # (best_sigmoid, expected_tier, actual_tier)
    for entry in dataset:
        out = run(entry["query"])
        retrieval = evaluate_retrieval(out["retrieved_chunks"], entry)
        answer = evaluate_answer(out["answer"], out["tier"], entry)
        results.append(EvalResult(
            query=entry["query"], difficulty=entry.get("difficulty", "medium"),
            retrieval=retrieval, answer=answer, category=entry.get("category", ""),
        ))
        calib.append((out["best_sigmoid"], entry.get("expected_tier", 1), out["tier"]))

    n = len(results) or 1
    report = EvalReport(
        results=results,
        overall_accuracy=sum(1 for r in results if r.answer.accuracy) / n,
        overall_recall_at_5=sum(r.retrieval.recall_at_5 for r in results) / n,
        tier3_rate=sum(1 for r in results if not r.answer.tier_correct) / n,
        hallucination_count=sum(1 for r in results if r.answer.has_hallucination),
    )
    print_report(report)

    actual_tier3 = sum(1 for _, _, a in calib if a == 3) / n
    print(f"\nActual Tier-3 routing rate: {actual_tier3:.1%}")

    if calibrate:
        print("\n=== Threshold calibration (best reranked sigmoid per query) ===")
        t1 = sorted(s for s, et, _ in calib if et == 1)
        t3 = sorted(s for s, et, _ in calib if et == 3)
        if t1:
            print(f"expected Tier-1 (n={len(t1)}): min={t1[0]:.3f} p10={t1[len(t1)//10]:.3f} "
                  f"median={t1[len(t1)//2]:.3f} max={t1[-1]:.3f}")
        if t3:
            print(f"expected Tier-3 (n={len(t3)}): min={t3[0]:.3f} median={t3[len(t3)//2]:.3f} max={t3[-1]:.3f}")
        for s, et, a in sorted(calib):
            flag = "" if et == a else "  <-- MISMATCH"
            print(f"  sigmoid={s:.3f}  expected_tier={et}  actual_tier={a}{flag}")


if __name__ == "__main__":
    main()
