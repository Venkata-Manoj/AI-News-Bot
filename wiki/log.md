# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete

## [2026-08-21] create | Wiki initialized (Karpathy LLM-Wiki pattern)
- Domain: AI-News-Bot (autonomous AI news intelligence system)
- Structure created with SCHEMA.md, index.md, log.md
- Bootstrapped 6 pages absorbing + superseding .hermes/repo-memory.md (stale 2026-07-12)
- Pages: ai-news-bot, ai-news-bot-architecture, llm-provider-fallback, testing-strategy, open-technical-debt
- Reason: HAES mandates LLM Wiki as project's primary long-term memory; none of 7 repos had one

## [2026-08-26] update | HAES adds dedup engine unit tests (PR #21)
- Added `tests/unit/test_dedup_unit.py` — 18 deterministic, fully-mocked tests for `modules/dedup.py`
- `modules/dedup.py` gated coverage 0% → 93%; repo TOTAL gated coverage 28% → 32%
- Gated `tests/unit/` suite: 54 → 72 tests; ruff clean + pytest green verified locally before push
- Updated ai-news-bot.md entity status; Closes roadmap "test coverage expansion"
- Branch: feature/2026-08-26-dedup-unit-tests → PR #21 (awaiting CI + user merge per branch-safety rule)
