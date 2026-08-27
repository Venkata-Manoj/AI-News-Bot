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

## [2026-08-27] update | HAES adds fetcher/apify pure-logic unit tests
- Added `tests/unit/test_fetcher_utils.py` — 32 deterministic, fully-mocked tests covering the
  untested pure helpers in `modules/fetcher.py` (strip_html, normalise_url, hash_url,
  extract_rss_text, Article) and `modules/apify_fetcher.py` (is_ai_related)
- Gated `tests/unit/` suite: 72 → 104 tests; ruff clean + pytest green verified locally before push
- 3 initial failures were fixture bugs (wrong `fetcher.hash_url("")` assumption; `_Entry` returning
  None instead of raising AttributeError) — fixed fixtures, production code confirmed correct
- Narrowed [[open-technical-debt]] "Broaden unit coverage" → only LLM provider *call* paths remain
- Branch: feature/2026-08-27-fetcher-utils-tests (per HAES branch-safety, awaits user merge)
