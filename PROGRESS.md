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
- [ ] Unit tests for `modules/formatter.py`
- [ ] Unit tests for `modules/dispatcher.py`
- [ ] Unit tests for `modules/youtube_fetcher.py`
