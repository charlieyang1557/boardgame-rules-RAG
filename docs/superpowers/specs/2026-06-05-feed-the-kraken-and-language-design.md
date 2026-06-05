# Spec: Add Feed the Kraken + global EN/ZH output language

**Date:** 2026-06-05
**Status:** Approved (design) — pending spec review
**Scope:** Add the board game *Feed the Kraken* (`ftk`) to the oracle, and add a
global English/Chinese **output-language** toggle that applies to every game.

---

## 1. Goals & non-goals

**Goals**
- Add `ftk` as a fully supported game: ingestion → retrieval → generation →
  golden-dataset eval, hitting the Phase-1 success bars.
- Accuracy is the top priority — FtK is a relatively simple, single-rulebook game.
- A global UI toggle to receive answers in **English** or **Chinese (中文)**,
  for all games, without degrading retrieval/answer accuracy.

**Non-goals (YAGNI)**
- Do **not** ingest the Chinese unofficial rules (incomplete blog summary →
  would hurt accuracy). The official English PDF is the single source of truth.
- Do **not** translate the English source-chunk "sources" panel (citations point
  at the official English rulebook).
- No Tier-2 multi-hop for FtK (single simple rulebook → 1 hop).
- UI-chrome localization is **minimal** (example questions + a handful of strings),
  not a full i18n of every visible string.

---

## 2. Part A — Feed the Kraken game (`ftk`)

### 2.1 Config (`routing/game_config.py`)
- `GAME_CONFIG["ftk"] = GameConfig(retrieval_hops=1, rerank_top_k=5,
  hybrid_top_k=20, rrf_k=60, multi_system_detection=False, use_secondary_kb=False,
  version_aware=False, parser_mode="agentic", tier1_threshold=<calibrated>)`.
  - `parser_mode="agentic"`: the rulebook is 2-column with icon sidebars; premium
    LlamaParse handles it far better than cost_effective.
  - `tier1_threshold` calibrated empirically on the golden set (Start-Instructions
    Step 8). Start from Splendor's default (0.25); document the chosen value.
- `INGESTION_CONFIGS["ftk"] = IngestionConfig(chunk_size=300, overlap=50,
  section_patterns={...})` relabeling the major rule sections:
  Setup, Victory Conditions, the 4 gameplay phases (Appointing the Navigation Team,
  A Question of Loyalty, The Navigation, Off-duty), Resolving a Mutiny,
  Executing the Navigation Card, Denial of Command, Emergency Navigation,
  Supply Line, Map Actions, Navigation Card Actions, Cult Ritual Cards,
  Becoming a Cultist, Character Cards. (Refined after inspecting the parse.)
- `TERMINOLOGY_MAPS["ftk"]`: ~20 colloquial→rulebook mappings. Draft:
  - "vote"/"voting"/"overthrow"/"rebel" → "mutiny"
  - "first mate" → "lieutenant"; "helmsman"/"pilot" → "navigator"
  - "direction card"/"course card" → "navigation card"
  - "pistol"/"weapon" → "gun"
  - "role card" → "character card"; "team"/"side" → "faction"
  - "silence"/"cut tongue"/"cut out tongue" → "off with the tongue"
  - "sacrifice"/"throw overboard to the kraken" → "feed the kraken"
  - "brainwash"/"convert" → "conversion to cult"
  - "check bag"/"search bag" → "cabin search"
  - "blue area"/"sailor goal" → "Bluewater Bay"
  - "red area"/"pirate goal" → "Crimson Cove"
  - "rum" → "Drunk navigation card"
  - "skip"/"sit out" → "off-duty"
  - "refuse to steer"/"jump overboard" → "denial of command"
- `PDF_SOURCES["ftk"] = [("data/rulebooks/ftk.pdf", "ftk_rules")]`.
- No `LOCATION_NAMES` entry (FtK has no location-action mechanic like Speakeasy).

### 2.2 Ingestion (hybrid parse + diagnostic)
The PDF is at `data/rulebooks/ftk.pdf` (20 pages, present).
1. `build_primary_kb("ftk", "data/rulebooks/ftk.pdf")` → LlamaParse agentic →
   `ingestion/cache/ftk_parsed.json`.
2. **Parse diagnostic**: diff the LlamaParse text against the verbatim rulebook
   text (held in the working session) to flag dropped/garbled content
   (2-column merges, lost icon captions, dropped tables like the mutiny
   gun-threshold table and team-composition table). Hand-correct
   `ftk_parsed.json` where LlamaParse mangled it, then re-embed. This delivers
   the standard pipeline **and** a fidelity guarantee.
3. Verify: chunk count == Pinecone `ftk` namespace vector count == BM25 pickle
   count (the startup staleness guard).

### 2.3 Golden dataset (`evaluation/golden_dataset/ftk.json`)
Written **first** (TDD). ~30 English questions with `ground_truth`,
`expected_tier`, `required_chunk_keywords`, `forbidden_content`, `difficulty`.
Coverage:
- Victory conditions per faction (Sailors→Bluewater Bay east; Pirates→Crimson
  Cove west; Cult→Kraken north or Cult Leader fed to Kraken).
- Mutiny gun thresholds by player count (5–7→3, 8–9→4, 10–11→5).
- Navigation team appointment + exceptions (captain can't appoint self;
  off-duty can't be appointed; lieutenant≠navigator).
- The navigation draw/discard flow (captain draws 2, lieutenant draws 2, each
  discards 1, navigator discards 1, captain reveals last).
- Navigation card actions: Drunk, Mermaid, Telescope, Armed, Disarmed, Cult Uprising.
- Map actions: Cabin Search, Flogging, Off with the Tongue, Feed the Kraken.
- Cult rituals (Conversion to Cult / Cult's Guns Stash / Cult Cabin Search) +
  "convertible player" rules (cabin-searched/flogged players become unconvertible).
- Denial of command + emergency navigation; off-duty signs by player count;
  supply line (long journey only); reshuffle (<4 cards); 5-player variable
  composition; cult-leader-fed-to-kraken = cult win.
- Include a couple of expected-Tier-3 questions (rules genuinely not covered).
Then calibrate the threshold and iterate to: Tier-1 >90%, recall@5 >85%,
Tier-3 <10%, zero hallucinations.
- **Adversarial verification:** after drafting, a verification pass checks every
  `ground_truth` against the official rulebook text before the dataset is trusted.

### 2.4 Frontend
- `GAMES` += `{ displayName: "Feed the Kraken", apiKey: "ftk" }`.
- `EXAMPLE_QUESTIONS.ftk` = 3 representative questions (EN), with ZH variants
  (see §3.4).

---

## 3. Part B — Global EN/ZH output-language toggle

**Core principle:** retrieval, generation, and citation verification stay 100%
English against the official rulebook. Only the *final, already-verified* answer
is translated. The tested verification path is unchanged.

### 3.1 Request / API (`api/main.py`)
- `AskRequest` += `language: str = "en"` (validated to `{"en","zh"}`; invalid →
  fall back to `"en"`).
- `language` threaded through `_run_pipeline`.

### 3.2 Query rewriter (`retrieval/query_rewriter.py`)
- System prompt strengthened: **always** output the rewritten `QUERY:` line in
  **English** using official rulebook terminology, even when the user's question
  is in another language. (One-line change; helps every game; makes Chinese input
  retrievable against the English KB + English cross-encoder.)

### 3.3 Translation (`generation/translator.py` — new module)
- `translate_answer(answer_en: str, target_lang: str, anthropic_client) -> str`
  using Haiku (cheap/fast). `target_lang == "en"` → return input unchanged
  (no API call).
- Invoked in `_run_pipeline` **after** citation verification, only when
  `language == "zh"`.
- Translation instruction: faithful, preserve `[chunk_id]` markers verbatim
  (frontend strips them). Use natural board-game Chinese terminology; do not add
  or omit rules. Output Simplified Chinese (简体中文).
- **Tier handling:**
  - Tier 1 / Tier 2 (official answers): verify in English → translate verified
    answer to ZH.
  - Tier 3 (uncertainty): localize fixed boilerplate labels via a tiny i18n map;
    the "suggested interpretation" (already a Haiku call, explicitly non-official)
    is generated **directly** in the target language; raw closest-chunk excerpts
    stay verbatim English (official text). Implemented by passing `language` into
    `generate_tier3`.

### 3.4 Caching & logging
- `cache/semantic_cache.py`: add a parallel `languages: list[str]` array; `lookup`
  and `store` gain a `language` param; a hit requires matching game **and**
  language. (A ZH user never receives a cached EN answer.)
- `query_logging/query_logger.py`: add a `language` column (safe
  `ALTER TABLE ... ADD COLUMN language TEXT DEFAULT 'en'` migration guarded by a
  PRAGMA/try-except so existing DBs upgrade cleanly); `log_query` gains a
  `language` param.

### 3.5 Frontend
- New `LanguageSelector` component mirroring `GameSelector` styling; options
  `EN` / `中文`. Placed in the header next to the game selector.
- `App.tsx`: `language` state, persisted to URL `?lang=`, passed to `useChat`.
- `useChat`: include `language` in the `/ask` body.
- **Minimal chrome localization** via a small i18n map keyed by language:
  input placeholder, error toast, "Sources" label, tier labels. Plus ZH variants
  of `EXAMPLE_QUESTIONS`. Nothing else localized.

---

## 4. File-by-file change list

**Backend**
- `routing/game_config.py` — FtK GameConfig, IngestionConfig, terminology map,
  PDF_SOURCES.
- `generation/translator.py` — **new**: `translate_answer`.
- `generation/generator.py` — `generate_tier3` gains `language` (label i18n +
  interpretation in target language).
- `retrieval/query_rewriter.py` — always-English output instruction.
- `cache/semantic_cache.py` — language-aware keying.
- `query_logging/query_logger.py` — `language` column + param (migration-safe).
- `api/main.py` — `language` in `AskRequest`, threaded through pipeline; translate
  after verification; cache/log with language.
- `ingestion/cache/ftk_parsed.json` — generated + hand-corrected.
- `ingestion/cache/ftk_bm25.pkl` — generated by ingestion.
- `evaluation/golden_dataset/ftk.json` — **new**.

**Frontend**
- `frontend/src/constants.ts` — `ftk` in `GAMES`, `EXAMPLE_QUESTIONS.ftk`, i18n
  map, ZH example variants.
- `frontend/src/components/LanguageSelector.tsx` — **new**.
- `frontend/src/App.tsx` — language state + URL param + header placement.
- `frontend/src/hooks/useChat.ts` — send `language`.
- `frontend/src/types.ts` — `AskRequest.language`; `Game`/i18n types as needed.

---

## 5. Testing (TDD — tests first)

**Backend (pytest)**
- `tests/test_translator.py` — ZH output non-empty + `[chunk_id]` markers
  preserved; EN passthrough returns input unchanged with no API call (mock).
- `tests/test_semantic_cache.py` — extend: same embedding, different language →
  cache miss; same game+language → hit.
- `tests/test_query_rewriter.py` — extend: Chinese input → English `QUERY:` line.
- `tests/test_query_logger.py` — extend: `language` stored/retrieved; migration on
  a pre-existing DB without the column.
- `tests/test_api.py` — extend: `/ask` accepts `language`; invalid value → `en`.

**Frontend (vitest)**
- `LanguageSelector` renders options and fires `onChange`.
- `useChat` includes `language` in the request body.
- `App` reads/writes `?lang=` and wires the selector.

**Eval**
- `evaluation/golden_dataset/ftk.json` run via `eval_runner` for retrieval +
  answer accuracy (English ground truth).
- A couple of dedicated ZH translation smoke checks (answer is Chinese; markers
  preserved).

---

## 6. Success criteria (Phase-1 bars for FtK)
- Tier-1 accuracy > 90% on the golden dataset.
- Top-5 retrieval recall > 85%.
- Tier-3 rate < 10%.
- Zero hallucinations (citation verifier).
- `/health` lists `ftk` in `games_loaded`; BM25 count == Pinecone `ftk` vectors.
- Language toggle: ZH answers are faithful Chinese translations of the verified
  English answers; EN path unchanged (no regression on existing games).

---

## 7. Operational notes
- Ingestion hits OpenAI embeddings + Pinecone (`ftk` namespace, additive/safe on
  the shared index) + LlamaParse (agentic quota). Keys are present in `.env`.
- `.env` values must stay shell-safe (Stop hook sources `.env`).
- After each Python edit: `ruff check . --fix`; run the relevant test file.
- Never commit with failing tests.
