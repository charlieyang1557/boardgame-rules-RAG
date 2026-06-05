# Phase 5 — Feed the Kraken + Global EN/ZH Output Language

**Date:** 2026-06-05
**Spec:** `docs/superpowers/specs/2026-06-05-feed-the-kraken-and-language-design.md`

Adds the board game *Feed the Kraken* (`ftk`) and a global English/Chinese
output-language toggle for every game.

---

## Part A — Feed the Kraken metrics (golden dataset, 38 questions)

| Metric | Target | Result |
|---|---|---|
| Tier-1 answer accuracy | > 90% | **100%** (36/36 in-scope) |
| Overall accuracy | — | 97.4% (only miss: a tier-3 meta-question) |
| Retrieval recall@5 (keyword hit) | > 85% | **100%** |
| Tier-3 routing rate | < 10% | **2.6%** |
| Hallucinations | 0 | **0** |
| `/health` lists `ftk` | yes | yes |

Per-category accuracy: victory, mutiny, setup, navigation, nav_card_actions,
map_actions, cult, off_duty, edge_cases all **100%**.

### Calibrated threshold
`tier1_threshold = 0.25`. All 36 in-scope questions score reranker sigmoid
≥ 0.60 (median 0.998); out-of-scope meta-questions also score high, so the
threshold cannot separate them. Per project guidance, citation verification is
the primary quality gate — a low threshold plus the generator's "say so if not
enough info" handles out-of-scope. Raising to ~0.60 would put the lowest real
question (0.604) on a razor-thin margin, so it was rejected.

### Ingestion (hybrid parse)
LlamaParse agentic was run first, but the dense 2-column layout bled
author-bio/credits text into the rules pages and mislabeled sections. The parse
cache (`ingestion/cache/ftk_parsed.json`) was therefore **hand-corrected** from
the rulebook text into 28 clean, faithful sections → **29 chunks**. Counts match
across the staleness guard: 29 chunks == 29 Pinecone `ftk` vectors == 29 BM25
docs. Raw LlamaParse output was kept only for diagnosis (not committed).

---

## Part B — Global EN/ZH output language

**Principle:** retrieval, generation, and citation verification always run in
English against the official rulebook; only the final **verified** answer is
translated (verify-then-translate). The accuracy-critical path is unchanged.

- **`generation/translator.py`** (new): `translate_answer()` via Haiku.
  English/blank input is a no-op; translation failure falls back to English;
  `[chunk_id]` citation markers are preserved verbatim. Output is Simplified
  Chinese (简体中文).
- **Query rewriter**: always emits an English retrieval query (so Chinese input
  is retrievable against the English KB + English cross-encoder).
- **Tier 3**: boilerplate labels localized; interpretation generated directly in
  the target language; closest-chunk excerpts stay verbatim English.
- **Semantic cache**: partitioned by `(game, language)` — a ZH user never gets a
  cached EN answer.
- **Query log**: `language` column added with a migration that upgrades
  pre-existing DBs.
- **API**: `AskRequest.language` (`en`/`zh`, invalid → `en`); threaded through
  the pipeline; translation applied after verification.
- **Frontend**: `LanguageSelector` (EN / 中文) in the header, `?lang=` URL param,
  `language` in the `/ask` body, ZH example questions, and minimal UI-chrome
  localization (placeholder, errors, Sources, tier labels, empty-state, loading).

### ZH smoke test (live)
Chinese answers are faithful (蓝水湾 = Bluewater Bay, 叛变 = mutiny, 邪教领袖 =
Cult Leader), citation markers preserved, tier-1 routing, English source chunks
still returned. EN and ZH answers differ for the same question.

---

## Verification

- **Backend:** 152 pytest tests pass (translator, cache language partitioning,
  logger migration, rewriter English output, tier-3 i18n, API language model).
- **Frontend:** 15 vitest tests pass; `eslint` clean; `tsc -b && vite build` clean.
- **No regression:** Catan before/after the rewriter change — original prompt
  82.9%, new prompt 85.7% (neutral/slightly positive), both 0 hallucinations /
  100% recall@5. Splendor 97.1%, 0 hallucinations. (The stale April PHASE docs'
  higher numbers came from a different, uncommitted harness; the new committed
  harness `evaluation/run_pipeline_eval.py` measures consistently.)

---

## Review gate (3 independent reviews)

Three independent reviews were run on the diff and all actionable findings fixed
(tests still green after each round):

- **code-reviewer:** 0 critical, 2 HIGH — fixed: eval harness now mirrors the
  production verify-then-translate guard; session history stores the **English**
  answer (consumed only by the English-output rewriter) on both the live and
  cache-hit paths (cache now also stores `answer_en`). Plus: migration race
  guard, eval `--lang` bounds check, frontend `AbortController` for in-flight
  cancellation, default eval game `splendor`.
- **security-reviewer:** 0 critical, 0 high. Hardened anyway: translator wraps
  the answer in a `<answer>` data envelope (prompt-injection defense), language
  fallback is `"English"` not the raw code, cache `max_size` raised to 1000 for
  the added language dimension. Confirmed clean: parameterized SQL, validated
  input (Pydantic + pipeline guard), no secrets, ReactMarkdown-safe rendering,
  validated `?lang`/`?game`, bounded cache.
- **Codex (adversarial):** found a **pre-existing** control-flow bug — on a
  Tier-1 citation-verification failure, the intended Tier-2 escalation for
  multi-hop games (Speakeasy/FCM) never executed (reassigning `tier_decision`
  does not re-enter the `elif`), so an **unsupported** answer was being served
  (and, under ZH, translated and cached). Fixed: Tier-1 verification failures
  now fall back to **Tier 3** uniformly (what FtK already did and what the eval
  harness measures). Also added a ZH cache guard (don't cache a failed
  translation under the `zh` key) and a frontend post-body abort guard.
  - Note: this changes Speakeasy/FCM behavior on Tier-1 verification failure
    (Tier 3 instead of a broken/unsupported answer). It aligns production with
    the eval harness; a fresh Speakeasy/FCM golden run is recommended to confirm
    metrics but was not re-run in this session.

## Files

**New:** `generation/translator.py`, `evaluation/golden_dataset/ftk.json`,
`evaluation/run_pipeline_eval.py`, `frontend/src/components/LanguageSelector.tsx`,
`frontend/src/__tests__/LanguageSelector.test.tsx`, `tests/test_translator.py`,
`ingestion/cache/ftk_bm25.pkl`, `ingestion/cache/ftk_parsed.json` (hand-corrected).

**Modified:** `routing/game_config.py` (ftk config + terminology + ingestion +
PDF source), `api/main.py`, `cache/semantic_cache.py`,
`query_logging/query_logger.py`, `retrieval/query_rewriter.py`,
`generation/generator.py`, and the frontend (`constants.ts`, `types.ts`,
`App.tsx`, `hooks/useChat.ts`, `components/ChatWindow.tsx`, `InputBar.tsx`,
`MessageBubble.tsx`) + their tests.

### Commit guidance
- **Commit** the code changes + `ingestion/cache/ftk_bm25.pkl` (needed for the
  Railway deploy, like the other games' pickles).
- **Force-add `ingestion/cache/ftk_parsed.json`** (`git add -f`): it is normally
  gitignored, but FtK's cache is hand-corrected and **not** reproducible by
  re-running LlamaParse, so it should be version-controlled.
- `data/rulebooks/ftk.pdf` is ~19 MB and not needed at runtime — committing it is
  optional (the app uses the BM25 pickle + Pinecone). Your call.

## Known limitations
- Out-of-scope meta-questions (playing time, age) route to Tier 1 with a
  "not specified" answer rather than Tier 3 (score-based routing can't separate
  topically-adjacent out-of-scope questions).
- Source-chunk excerpts stay English in ZH mode (citations to the official
  English rulebook) — by design.
- ZH defaults to Simplified Chinese; switch the target in
  `generation/translator.py::LANGUAGE_NAMES` for Traditional.
