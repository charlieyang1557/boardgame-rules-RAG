# Phase 1b — Multi-Game Validation Complete

## Catan Metrics
- **Tier 1: 28/30 (93%)** — PASS (target > 90%)
- **Tier 3: 2/30 (7%)** — PASS (target < 10%)
- Tier 3 mismatches: "cost to build a road" (retrieval miss), "distance rule" (retrieval miss)
- Ingestion: 89 chunks, 16 pages, 42K chars
- Pinecone: 89 vectors in `catan` namespace
- BM25: 89 documents in catan_bm25.pkl

## Splendor Regression
- **Tier 1: 25-29/30 (83-97%)** — varies by run due to citation verifier non-determinism
- Retrieval and routing are stable (93%+ in isolation)
- The variance is entirely from the LLM-based citation entailment check producing
  different results across Sonnet calls

## Cross-Game Isolation — All 8 Tests Pass
- Cache partitioned by game_name: splendor cache miss for catan query
- Per-game searcher dict: splendor searcher has only splendor chunk IDs
- Catan searcher has only catan chunk IDs
- Searcher chunk ID sets are fully disjoint
- GAME_CONFIG validates unknown games

## Architecture Changes
- Global `_searcher` → per-game `_searchers` dict (lazy init)
- `game_name` is now required in API requests (no more implicit splendor default)
- Health endpoint reports `games_loaded` list instead of single boolean
- Hard-coded splendor guard removed, replaced with GAME_CONFIG validation

## Phase 1 Bugs Discovered
1. **Pinecone batch size** — free tier connection drops with batch_size=100.
   Fixed: reduced default to 20.
2. **Citation verifier non-determinism** — the remaining reliability issue.
   The LLM entailment check (Step 2 of verification) produces different verdicts
   across Sonnet calls. This causes 5-15% variance in Tier 1 rate per run.
   Root cause: Sonnet is non-deterministic; the entailment prompt is ambiguous
   for paraphrased claims. Fix requires either: (a) more precise entailment prompt,
   (b) temperature=0 on verification calls, or (c) multiple-run voting.

## Threshold Analysis
- Splendor: 0.25 threshold works (bimodal: 28/30 > 0.79, 2/30 < 0.04)
- Catan: 0.25 threshold works (similar bimodal distribution, clean gap)
- No per-game thresholds needed — universal 0.25 is sufficient for both games

## Test Suite
- **99 unit tests** passing (91 core + 8 cross-game isolation)
- Ruff clean

## Ready for Phase 2?
**Conditionally ready.** The multi-game architecture is validated and working.
The remaining concern is citation verifier reliability — it introduces 5-15%
variance in Tier 1 accuracy per run. This should be stabilized before adding
Speakeasy/FCM (Phase 2a) to avoid compounding non-determinism across more games.

Recommended pre-Phase 2 fix: add `temperature=0` to the Sonnet verification call
and/or tighten the entailment prompt to reduce ambiguity.
