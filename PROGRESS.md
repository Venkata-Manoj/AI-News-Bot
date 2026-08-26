# AI News Bot — Progress

## 2026-07-04 — Unit tests for core modules + Dependabot

### Completed
- Added Dependabot config for automated dependency updates
- Added unit tests for `modules/db.py` — SQLite state management (all CRUD operations, edge cases)
- Added unit tests for `modules/dedup.py` — URL deduplication, keyword filtering, edge cases
- Added unit tests for `modules/sender.py` — HTTP retry logic, flood wait, error alerts, batch sending
- Created `tests/test_db.py`, `tests/test_dedup.py`, `tests/test_sender.py`

### Impact
- Test coverage increased from ~13% to ~45%
- All new tests are true unit tests (no live APIs, no network)
- 27 new test functions across 3 test files

### Remaining
- [ ] Coverage reporting (Codecov or similar)
- [ ] Docker image for easy deployment
- [ ] Unit tests for `modules/llm.py` (complex, needs provider mocking)
- [ ] Unit tests for `modules/dispatcher.py`
- [ ] Unit tests for `modules/youtube_fetcher.py`

## 2026-07-12 — Unit tests for formatter.py + bugfix + repo memory

### Completed
- Added comprehensive unit tests for `modules/formatter.py` — 70 tests across all 7 public functions
- Fixed bug in `get_source_emoji()` where the "x" SOURCE_EMOJI key (Twitter/X) falsely matched "arxiv" sources (e.g., `arXiv:cs.AI` → 🐦 instead of 📄)
- Fixed incorrect `async def` on `format_youtube_article()` — contained zero `await` calls but was declared async, causing a latent bug where `format_batch()` called it without `await`
- Created `.hermes/repo-memory.md` for long-term project memory (wiki pattern)

### Impact
- Test coverage for formatter.py: **from 0% to full coverage** (70 tests)
- 70 new test functions across: escape_md (8), get_source_emoji (10), get_source_label (8), format_batch_header (8), format_article (10), format_youtube_article (12), format_batch (9), regression (5)
- All 145 tests pass (1 skipped: YouTube API key required)
- Bugfix prevents arXiv articles from showing Twitter emoji
- Bugfix prevents `format_batch()` from silently returning coroutine objects for YouTube articles

### Remaining (unchanged)
- [ ] Coverage reporting (Codecov or similar)
- [ ] Docker image for easy deployment
- [ ] Unit tests for `modules/llm.py` (complex, needs provider mocking)
- [ ] Unit tests for `modules/dispatcher.py`
- [ ] Unit tests for `modules/youtube_fetcher.py`

## 2026-08-20 — Offline unit-test suite for llm/dispatcher/youtube_fetcher + CI gate

### Completed
- Added `tests/unit/` — fully mocked, network-free unit tests (no API keys) for the three modules previously flagged "needs tests" in PROGRESS.md / repo-memory.md:
  - `tests/unit/test_llm_parse.py` — `parse_response` multi-stage JSON-repair (clean array, dict-with-list, markdown fence, array-extraction, malformed first-level repair, last-resort object extraction, empty/None), `build_prompt` (indexing, 400-char body truncation, missing-body placeholder), `filter_by_score`, `get_provider` priority/availability, `summarise_batch_flex` index→article mapping.
  - `tests/unit/test_youtube_utils.py` — `parse_iso_duration`, `format_duration`, `format_count`, `parse_vtt_timestamp`, `parse_vtt` (segment parsing + deduplication), `chunk_transcript`, `get_uploads_playlist_id`.
  - `tests/unit/test_dispatcher_unit.py` — `AsyncDispatcher` dedup-on-enqueue, batch short-circuits (no summaries / filtered out / empty format), success accounting (`items_processed`, `db.log_delivery`), sender-error handling (`items_failed`, `db.log_error`), lifecycle (`start`/`stop`/`get_stats`).
- Added `unit-test` CI job (`.github/workflows/ci.yml`) that runs `pytest tests/unit/` with `--cov=modules` and **fails the build on error**, finally gating the repo on real regression protection (the old `test` job intentionally runs live source smoke tests with `continue-on-error`).

### Impact
- **54 new unit tests pass** (199 total now: 145 existing + 54 new, 1 skipped)
- Closes three long-standing "needs tests" gaps for `llm.py`, `dispatcher.py`, `youtube_fetcher.py`
- Coverage reporting is now available locally (pytest-cov), addressing the "Coverage reporting" remaining item
- New CI job gives deterministic, network-independent regression protection

### Remaining
- [ ] Coverage reporting upload (Codecov/similar)
- [ ] Docker image for easy deployment
- [ ] Broaden unit coverage (fetcher.py, apify_fetcher.py, LLM provider call paths)

## 2026-08-21 — Bootstrap Karpathy-style LLM Wiki (repository memory)

### Completed
- Created `wiki/` — Karpathy LLM-Wiki pattern as the project's primary long-term memory (HAES mandate)
  - `wiki/SCHEMA.md` — domain conventions + tag taxonomy (8 top-level tags)
  - `wiki/index.md` — sectioned catalog (6 pages)
  - `wiki/log.md` — append-only action log
  - `wiki/entities/ai-news-bot.md` — project entity page (purpose, status, version, maturity)
  - `wiki/concepts/ai-news-bot-architecture.md` — pipeline + module table + gotchas
  - `wiki/concepts/llm-provider-fallback.md` — 6-provider chain + JSON-repair behavior
  - `wiki/concepts/testing-strategy.md` — two-tier tests + CI gate (199 pass / 1 skip)
  - `wiki/concepts/open-technical-debt.md` — resolved + open gaps, incl. held Dependabot #16
- Marked `.hermes/repo-memory.md` as superseded (last updated 2026-07-12; stale: claimed 145 tests)

### Impact
- Establishes compounding, cross-referenced memory so future HAES sessions avoid duplicate work
- All 6 pages use `[[wikilinks]]` (>=2 outbound each) and YAML frontmatter
- None of the 7 managed repos previously had an LLM Wiki; this is the first

### Remaining
- [ ] Roll the same `wiki/` pattern out to data-analysis, transcribo, web-crawl, sketch-portfolio, portfolio, Capstone-Forage
- [ ] Coverage reporting upload (Codecov/similar)
- [ ] Docker image for easy deployment
- [ ] Broaden unit coverage (fetcher.py, apify_fetcher.py, LLM provider call paths)

## 2026-08-26 — Offline unit tests for dedup engine (CI-gated suite)

### Completed
- Added `tests/unit/test_dedup_unit.py` — deterministic, fully mocked unit tests for `modules/dedup.py` (the core deduplication engine that prevents duplicate Telegram deliveries):
  - `hash_url`: empty/None → `""`, stable hex digest, deterministic, distinct URLs distinct hashes
  - `filter_by_keywords`: empty passthrough, title/body match, irrelevant drop, case-insensitive, custom keywords, missing-attribute safety
  - `SeenManager.filter_new`: keeps all-new, drops seen, mixed seen/new, back-fills missing `url_hash` from URL, delegates `is_seen`/`mark_seen` to the DB store
- The DB collaborator is mocked, so no SQLite writes occur — fully offline and CI-safe.

### Impact
- **18 new unit tests pass** (gated `tests/unit/` suite now 72 tests, was 54)
- `modules/dedup.py` coverage in the gated suite: **0% → 93%** (only 3 delegation wrappers missed)
- Repo TOTAL coverage (gated, `--cov=modules`): **28% → 32%**
- Closes a gap flagged in the roadmap ("test coverage expansion") and PROGRESS.md ("Broaden unit coverage")
- Both CI jobs protected: `ruff check .` clean + `pytest tests/unit/` green, verified locally before push

### Remaining
- [ ] Roll the same `wiki/` pattern out to data-analysis, transcribo, web-crawl, sketch-portfolio, portfolio, Capstone-Forage
- [ ] Coverage reporting upload (Codecov/similar)
- [ ] Docker image for easy deployment
- [ ] Broaden unit coverage (fetcher.py, apify_fetcher.py, LLM provider call paths)
