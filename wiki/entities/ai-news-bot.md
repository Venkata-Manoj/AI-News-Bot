---
title: AI-News-Bot
created: 2026-08-21
updated: 2026-08-26
type: entity
tags: [architecture, pipeline, roadmap, ci, testing]
sources: [../.hermes/repo-memory.md, README.md, PROGRESS.md]
confidence: high
---

# AI-News-Bot

## Overview
Autonomous AI news intelligence system. Monitors **6 source types** (RSS, Reddit,
Twitter/Nitter, YouTube, Hacker News, arXiv), summarizes with a **6-provider LLM fallback
chain**, and delivers curated, scored updates to **Telegram** on a 45-minute schedule.

## Key Facts
- **Owner:** Venkata-Manoj (B.V Manoj)
- **Language / Runtime:** Python 3.11 (requires-python >=3.10)
- **Current version:** v3.0.0 (pyproject.toml; README still narrates v3.0 highlights)
- **License:** MIT
- **Maturity:** Production-leaning / "Beta" classifier (pyproject `Development Status :: 4 - Beta`)
- **Default branch:** `main`; CI green on last push (2026-08-20)
- **Active repo:** Most recently pushed of the 7 managed repos (2026-08-24T17:46Z user push; HAES resumed 2026-08-26)

## Status (as of 2026-08-26)
- 217 unit tests pass total (199 prior + 18 added 2026-08-26); gated `tests/unit/` suite = 72 tests (was 54)
- Deterministic offline `unit-test` CI job gates the repo on regression (added 2026-08-20)
- **2026-08-26 HAES:** added `tests/unit/test_dedup_unit.py` — `modules/dedup.py` gated coverage **0% → 93%**, repo TOTAL gated coverage **28% → 32%** (PR #21). Closes roadmap "test coverage expansion".
- Dependabot open PRs #19 (python-dotenv 1.2.2→1.2.3), #20 (lxml 6.1.1→6.1.2) — held pending user approval per AGENTS.md "don't update deps without asking"
- **No LLM Wiki before 2026-08-21** — this `wiki/` bootstraps the project's long-term memory (see [[ai-news-bot-architecture]])

## Relationships
- Pipeline components: [[ai-news-bot-architecture]]
- Resilience design: [[llm-provider-fallback]]
- Quality assurance: [[testing-strategy]]
- Remaining gaps: [[open-technical-debt]]

## Source References
- README.md (features, architecture, version history)
- PROGRESS.md (2026-07-04, 2026-07-12, 2026-08-20 sessions)
- `.hermes/repo-memory.md` (superseded; last updated 2026-07-12)
