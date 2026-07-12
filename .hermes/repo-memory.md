# AI News Bot — Repository Memory

## Repo Purpose
Autonomous AI news intelligence system that monitors 6 sources (RSS, Reddit, Twitter, YouTube, Hacker News, arXiv), summarizes with multi-provider LLM fallback, and delivers curated updates to Telegram.

## Tech Stack
- Python 3.11, APScheduler (scheduling), SQLite (state), httpx/aiohttp (HTTP)
- Multi-provider LLM: Gemini (primary), NVIDIA NIM, OpenRouter, Groq, Ollama, LM Studio
- YouTube: Data API v3 + yt-dlp (transcripts)
- Testing: pytest (145 unit tests), no network tests

## Architecture
```
main.py → APScheduler → fetcher.py (source router) → dedup.py → llm.py (LLM) → formatter.py → sender.py (Telegram)
dispatcher.py → async queue, batching, rate limiting
db.py → SQLite state (7 tables: seen_urls, daily_calls, source_state, error_log, delivery_log, youtube_videos, youtube_comments)
```

## Modules
| Module | Size | Status | Tests |
|--------|------|--------|-------|
| config.py | 128 lines | Stable | N/A (env vars) |
| dedup.py | ~80 lines | Stable | test_dedup.py (21 tests) |
| db.py | ~280 lines | Stable | test_db.py (28 tests) |
| sender.py | ~110 lines | Stable | test_sender.py (17 tests) |
| formatter.py | 255 lines | Stable | test_formatter.py (70 tests) |
| dispatcher.py | 204 lines | Needs tests | Not yet |
| llm.py | 577 lines | Stable | Not yet (complex mocking) |
| youtube_fetcher.py | ~580 lines | Stable | Not yet (API-heavy) |
| apify_fetcher.py | ~160 lines | Stable | Indirect via source tests |
| fetcher.py | ~280 lines | Stable | Indirect via source tests |

## Testing Status (as of 2026-07-12)
- **145 tests pass**, 1 skipped (YouTube API key required)
- Coverage: db.py ✅, dedup.py ✅, sender.py ✅, formatter.py ✅
- Pending: llm.py, dispatcher.py, youtube_fetcher.py, fetcher.py
- Source smoke tests: RSS ✅, HN ✅ (disabled), arXiv ✅, Reddit ✅, Twitter ✅, YouTube ⬜ (needs API key)

## LLM Fallback Chain
1. Gemini (gemini-2.5-flash) — 1000 RPD free tier
2. NVIDIA NIM (llama-3.3-nemotron-super-49b-v1)
3. OpenRouter (gemma-4-31b-it:free)
4. Groq (llama-3.1-8b-instant)
5. Ollama (local)
6. LM Studio (local)

## Key Conventions
- Conventional commits: feat:, fix:, chore:, refactor:, test:, ci:, docs:
- Version in README (currently v3.0)
- PROGRESS.md updated with every change
- `.env` file required (not committed)
- AGENTS.md maintained with architecture, commands, gotchas
- Tests in `tests/` directory, conftest.py adds root to sys.path

## Known Technical Debt
1. llm.py needs unit tests (complex — needs provider mocking for 6 providers)
2. dispatcher.py needs unit tests (async, needs mocking for llm/sender/db)
3. youtube_fetcher.py needs tests (API-heavy)
4. No coverage reporting
5. No Docker image
6. SOURCE_EMOJI "x" key can falsely match words containing "x" (mitigated: arxiv checked first)

## Future Opportunities
- Docker Compose for one-command deploy
- Codecov or similar coverage reporting
- Type hints throughout (currently minimal)
- CI with GitHub Actions
- Support for more LLM providers
- Web dashboard for monitoring
