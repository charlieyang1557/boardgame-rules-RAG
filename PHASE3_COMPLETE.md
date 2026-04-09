# Phase 3 — Food Chain Magnate Complete

## Per-Game Accuracy (3-Run Validation)

| Game | Run 1 | Run 2 | Run 3 | Target | Status |
|------|-------|-------|-------|--------|--------|
| Splendor | 32/35 (91%) | 32/35 (91%) | 32/35 (91%) | > 90% | **PASS** |
| Catan | 32/35 (91%) | 32/35 (91%) | 32/35 (91%) | > 90% | **PASS** |
| Speakeasy | 41/50 (82%) | 42/50 (84%) | 41/50 (82%) | > 85% | MISS (3pp below) |
| FCM | 52/66 (79%) | 52/66 (79%) | 52/66 (79%) | > 80% | MISS (1pp below) |

### FCM Per-Tier Breakdown

| Tier | Accuracy | Target | Status |
|------|----------|--------|--------|
| Tier 1 (single-hop) | 22/31 (71%) | > 90% | Below — keyword overlap metric struggles with terse answers |
| **Tier 2 (multi-hop)** | **27/30 (90%)** | > 65% | **PASS** — 25pp above target |
| Tier 3 (unanswerable) | 3/5 (60%) | < 15% false answers | 2 queries get answers when they shouldn't |

### FCM Per-Category Breakdown

| Category | Accuracy | Target | Status |
|----------|----------|--------|--------|
| company_structure | 5/5 (100%) | - | **PASS** |
| setup | 4/4 (100%) | - | **PASS** |
| training | 5/5 (100%) | - | **PASS** |
| **milestone** | **10/11 (91%)** | >= 70% | **PASS** |
| **dinnertime** | **7/9 (78%)** | >= 70% | **PASS** |
| phase | 5/7 (71%) | - | OK |
| marketing | 5/7 (71%) | - | OK |
| employee | 9/14 (64%) | - | Below — answer phrasing differs from GT |
| general | 2/4 (50%) | - | Low — edge case queries |

## Canary Query Result

**PASS in all 3 runs.**

Query: "How much income do I get selling 1 burger and 2 beer to a house
with a garden, if I have the 'First burger marketed' milestone and
a luxury manager?"

System answer (Tier 1, single retrieval pass):
- Standard unit price: $10
- Luxury manager: +$10 → unit price = $20
- Garden doubles: 2 × $20 = $40 per item
- Burger milestone bonus: +$5 (not doubled by garden)
- **Burger: $40 + $5 = $45, Beer: $40 × 2 = $80, Total: $125** ✓

The system retrieved Dinnertime pricing rules, luxury manager effect,
garden doubling rules, AND the milestone bonus from the top-8 chunks
in a single retrieval pass — all 4 information sources needed.

## Tier 2 Hop Distribution

| Game | Tier 2 Queries | Resolved Hop 1 | Resolved Hop 2 | Resolved Hop 3 |
|------|---------------|----------------|----------------|----------------|
| Splendor | 5 | 5 (100%) | 0 | N/A |
| Catan | 5 | 5 (100%) | 0 | N/A |
| Speakeasy | 10 | 9 (90%) | 1 (10%) | N/A |
| FCM | 30 | 28 (93%) | 2 (7%) | 0 |

Most Tier 2 queries resolve at Hop 1 because:
1. FCM's rerank_top_k=8 (vs 5 for other games) retrieves more context
2. The section-aware chunking keeps related information together
3. The canary query ($125) resolves at Hop 1 with all 4 needed chunks in top-8

The 3-hop code path was tested and works (verified via unit tests with
mocked responses), but real queries rarely need it because the improved
chunking makes Hop 1 retrieval sufficient.

## Architecture Additions in Phase 3

### Config-Driven Chunking (new)
3-layer architecture for complex games:
- **game_config.py**: `IngestionConfig` + `SectionRule` dataclasses
  - `section_patterns`: regex → section name relabeling
  - `section_rules`: per-section keep_intact, split_pattern, max_chunk_size, create_index
- **pdf_parser.py**: Section relabeling using earliest-position-wins matching
  with carry-forward for multi-page sections
- **chunker.py**: Pre-chunk page merging for keep_intact sections,
  regex-based item splitting, section-aware index generation
- **kb_builder.py**: Reads chunk_size/overlap from IngestionConfig

Adding a new complex game is now a config change, not a code change.

### N-Hop Chain-of-Retrieval (refactored)
- `multi_hop.py` refactored from hardcoded 2-hop to N-hop loop
- Answerability check at every hop (was skipped at Hop 2)
- Existing chunk ID awareness prevents redundant retrieval
- Best-effort generation when max hops exhausted

### Per-Category Eval Reporting (new)
- `eval_runner.py` now supports optional category field
- `print_report` shows per-category accuracy and recall@5 breakdown

## Cost Per Query Analysis

| Path | Sonnet Calls | Haiku Calls | Embedding Calls | Est. Cost |
|------|-------------|-------------|-----------------|-----------|
| Tier 1 | 1-2 (gen + verify) | 1 (rewrite) | 1 | ~$0.01-0.02 |
| Tier 2 (2-hop) | 3 (answerable + gen + verify) | 1 | 2 | ~$0.03-0.04 |
| Tier 2 (3-hop) | 4 (2× answerable + gen + verify) | 1 | 3 | ~$0.04-0.05 |
| Tier 3 | 0-1 (optional Haiku interpretation) | 1-2 | 1 | ~$0.001-0.005 |

In practice: 93%+ of FCM queries resolve at Tier 1 cost.

## Cross-Game Summary

| Metric | Value |
|--------|-------|
| Total Pinecone vectors | ~350 (Splendor ~50 + Catan ~60 + Speakeasy ~185 + FCM 45) |
| Total golden dataset entries | 186 (Splendor 35 + Catan 35 + Speakeasy 50 + FCM 66) |
| Total tests | 131 |
| FCM chunks | 45 (13 milestone + 1 Dinnertime + 1 Marketing + 6 Employee + rest) |
| FCM calibrated thresholds | tier1=0.10, tier2=0.05 |

## Threshold Calibration Notes

FCM cross-encoder scores are bimodal — Tier 1, Tier 2, and Tier 3 queries
all score 0.8+ at the median. The cross-encoder (trained on web search)
cannot distinguish "answerable FCM question" from "unanswerable FCM question."

Thresholds at 0.10/0.05 effectively route everything to Tier 1, relying on
citation verification as the real quality gate. Tier 2 multi-hop triggers
when Tier 1 verification fails. This is architecturally correct — the verifier
catches bad answers regardless of routing.

Long-term fix: domain-adapted reranker (fine-tuning, out of scope for Phase 3).

## Known Limitations

1. **Speakeasy 82% (target 85%)**: 6-9 real failures on location details,
   solo/2-player setup specifics, and edge cases not well-covered by chunks.
   Fix: location-specific chunking overrides for Speakeasy (like FCM).

2. **FCM 79% (target 80%)**: 7 real pipeline failures:
   - Waitress answer truncated (generation issue)
   - Reserve card system confused with "on the beach" (retrieval gap)
   - 7 phases list incomplete (all phases not in one chunk)
   - New business developer misunderstood (retrieval returns general hiring)
   - Tiebreaker answer truncated
   - Milestone+salary calculation incomplete
   - Drive-in conflict query triggers game identification failure

3. **Eval metric**: 30% keyword overlap is fragile for verbose answers.
   Semantic similarity scoring (RAGAS) deferred to Phase 2 would help.

4. **3-hop code path untested in production**: Unit tests verify it works,
   but no real query triggered 3 hops because top-8 retrieval is sufficient.
   This is good (efficient) but means the 3-hop path lacks production validation.

## Assessment: Ready for Real Users?

**Partially.** The system handles Splendor and Catan well (91%). FCM's
multi-hop queries work surprisingly well (90% Tier 2 accuracy). The canary
query ($125 income calculation) passes perfectly in all 3 runs.

What works:
- Complex multi-hop queries across milestones, phases, and Dinnertime
- Citation verification catches hallucinations
- Config-driven chunking makes adding new games straightforward
- Honest Tier 3 responses when rules don't address the question

What needs improvement before real users:
- Speakeasy location coverage (add chunking overrides)
- FCM employee card retrieval (some cards not well-chunked)
- More robust eval metric (semantic similarity instead of keyword overlap)
- Production latency optimization (currently ~3-5s per query)
