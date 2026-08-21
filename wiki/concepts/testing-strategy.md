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

## Status (2026-08-20)
- **199 tests pass**, 1 skipped (YouTube API key required)
- Offline `unit-test` CI job runs `pytest tests/unit/ --cov=modules` and **fails the build on
  error** — real regression protection independent of network.
- `pytest-cov` available locally (coverage reporting was a prior "remaining" item, now
  addressable; upload to Codecov still pending — see [[open-technical-debt]]).

## History
- 2026-07-04: db/dedup/sender unit tests (~45% coverage)
- 2026-07-12: formatter.py 70 tests (0→full); bugfixes (arXiv emoji, async YouTube)
- 2026-08-20: llm/dispatcher/youtube_fetcher offline suite (+54 tests) + CI gate

## Related
- Pipeline: [[ai-news-bot-architecture]]
- Resilience: [[llm-provider-fallback]]
- Gaps: [[open-technical-debt]]
