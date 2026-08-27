---
title: Open Technical Debt
created: 2026-08-21
updated: 2026-08-21
type: concept
tags: [technical-debt, backlog, coverage, ci, deployment]
sources: [PROGRESS.md, .hermes/repo-memory.md]
confidence: high
---

# Open Technical Debt & Backlog

Tracked gaps for AI-News-Bot. Items struck through are resolved as of 2026-08-21.

## Resolved (this session's baseline)
- ~~llm.py unit tests~~ — done 2026-08-20 (test_llm_parse.py)
- ~~dispatcher.py unit tests~~ — done 2026-08-20 (test_dispatcher_unit.py)
- ~~youtube_fetcher.py unit tests~~ — done 2026-08-20 (test_youtube_utils.py)
- ~~Coverage reporting available locally~~ — pytest-cov wired 2026-08-20
- ~~fetcher.py + apify_fetcher.py pure-logic tests~~ — done 2026-08-27 (test_fetcher_utils.py,
  +32 tests; normalise_url/hash_url/strip_html/extract_rss_text/Article/is_ai_related)

## Open
1. **Coverage upload** — publish pytest-cov to Codecov/similar (local reporting exists, no upload)
2. **Docker image** — Dockerfile exists but no published image / Compose for one-command deploy
3. **LLM provider *call* paths** — `call_gemini / call_openrouter / call_groq / ...` in
   `modules/llm.py` (live HTTP, harder to mock deterministically) still lack direct unit tests;
   only parsing/fallback logic is covered (test_llm_parse.py)
4. **Type hints** — minimal across modules; pyproject ships `py.typed` but coverage is thin
5. **Web dashboard** — no monitoring UI for runs/deliveries
6. **Dependabot PR #16** (praw 8.0.2→8.0.3) — held pending user approval (AGENTS.md: ask before
   dependency updates). Patch is a bugfix (rewinds seekable file streams before retry).

## Related
- Tests: [[testing-strategy]]
- Architecture: [[ai-news-bot-architecture]]
- Project: [[ai-news-bot]]
