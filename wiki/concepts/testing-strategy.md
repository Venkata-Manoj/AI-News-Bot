---
title: Testing Strategy
created: 2026-08-21
updated: 2026-08-21
type: concept
tags: [testing, ci, coverage, module]
sources: [PROGRESS.md, README.md, .github/workflows/ci.yml]
confidence: high
---

# Testing Strategy

AI-News-Bot uses a **two-tier** testing approach: live source smoke tests (best-effort) and a
deterministic, network-free offline unit suite that gates CI.

## Tiers
1. **Live smoke tests** — `tests/run_all_tests.py` + `test_rss_feed.py`, `test_hn.py`,
   `test_arxiv.py`, `test_reddit.py`, `test_twitter.py`, `test_youtube.py`. Hit real sources
   (no LLM/Telegram). CI `test` job runs these with `continue-on-error` (Nitter/Twitter often
   blocked, HN disabled by default).
2. **Offline unit suite** — `tests/unit/` (fully mocked, no network/keys):
   - `test_llm_parse.py` — JSON-repair, prompt build, scoring, provider selection
   - `test_youtube_utils.py` — duration/count formatting, VTT parse, chunking
   - `test_dispatcher_unit.py` — AsyncDispatcher dedup/batching/lifecycle
- `test_fetcher_utils.py` — `strip_html`, `normalise_url`, `hash_url`, `extract_rss_text`,
  `Article` (fetcher.py) + `is_ai_related` (apify_fetcher.py) pure-logic coverage
- `test_llm_fallback.py` (2026-08-29) — `call_with_fallback` orchestration (order, availability,
  quota fall-through, falsy-result fall-through, all-fail→None), `call_openrouter`/`call_groq`/
  `call_nvidia` HTTP handling (200/429/404/retry), all with `httpx` faked → no network/SQLite

## Status (2026-08-29)
- **199 tests pass**, 1 skipped (YouTube API key required) — live suite unchanged
- Offline `unit-test` CI job: gated `tests/unit/` suite now **121 tests** (was 104 on 2026-08-27;
  120 passed + 1 xfailed documenting a latent `call_nvidia` 404-swallow bug), ruff clean;
  `pytest tests/unit/ --cov=modules` **fails the build on error** — real regression protection
  independent of network.
- `pytest-cov` available locally (coverage reporting was a prior "remaining" item, now
  addressable; upload to Codecov still pending — see [[open-technical-debt]]).
- Last untouched module: `formatter.py` (its behavior is already covered by `tests/test_formatter.py`,
  the live suite, so gated coverage is the only gap).

## History
- 2026-07-04: db/dedup/sender unit tests (~45% coverage)
- 2026-07-12: formatter.py 70 tests (0→full); bugfixes (arXiv emoji, async YouTube)
- 2026-08-20: llm/dispatcher/youtube_fetcher offline suite (+54 tests) + CI gate
- 2026-08-26: dedup engine offline suite (+18 tests); gated suite 54 → 72
- 2026-08-27: fetcher/apify pure-logic offline suite (+32 tests); gated suite 72 → 104
- 2026-08-29: LLM provider fallback orchestration offline suite (+17 tests); gated suite 104 → 121 (1 xfail = latent call_nvidia 404 bug)

## Related
- Pipeline: [[ai-news-bot-architecture]]
- Resilience: [[llm-provider-fallback]]
- Gaps: [[open-technical-debt]]
