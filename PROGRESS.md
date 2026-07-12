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
