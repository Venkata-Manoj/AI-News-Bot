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
- ~~LLM provider *call* paths~~ — done 2026-08-29 (test_llm_fallback.py, +17 tests;
  call_with_fallback + call_openrouter/call_groq/call_nvidia HTTP handling, httpx faked)

## Open
1. **Coverage upload** — publish pytest-cov to Codecov/similar (local reporting exists, no upload)
2. **Docker image** — Dockerfile exists but no published image / Compose for one-command deploy
3. **formatter.py gated coverage** — `modules/formatter.py` is only exercised by the *live* suite
   (`tests/test_formatter.py`), not the gated `tests/unit/` job. Behavior is already well
   covered; the gap is CI determinism, not correctness.
4. **`call_nvidia` 404 swallow** — `call_nvidia` raises a hard 404 (model not found) inside its
   own try/except loop and swallows it, returning `None`. A 404 should propagate so the fallback
   chain tries the next provider. Encoded as `xfail(strict=True)` in test_llm_fallback.py;
   flips to XPASS once fixed. (All other providers correctly raise on 4xx/5xx.)
5. **Type hints** — minimal across modules; pyproject ships `py.typed` but coverage is thin
6. **Web dashboard** — no monitoring UI for runs/deliveries
7. **Dependabot PR #16** (praw 8.0.2→8.0.3) — held pending user approval (AGENTS.md: ask before
   dependency updates). Patch is a bugfix (rewinds seekable file streams before retry).

## Related
- Tests: [[testing-strategy]]
- Architecture: [[ai-news-bot-architecture]]
- Project: [[ai-news-bot]]
