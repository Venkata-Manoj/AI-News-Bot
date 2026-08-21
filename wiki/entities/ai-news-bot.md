---
title: AI-News-Bot
created: 2026-08-21
updated: 2026-08-21
type: entity
tags: [architecture, pipeline, roadmap, ci]
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
- **Active repo:** Most recently pushed of the 7 managed repos (2026-08-20T15:49Z)

## Status (as of 2026-08-21)
- 199 unit tests pass (145 pre-existing + 54 added 2026-08-20), 1 skipped (YouTube API key required)
- Deterministic offline `unit-test` CI job gates the repo on regression (added 2026-08-20)
- Dependabot open PR #16 (praw 8.0.2→8.0.3) — held pending user approval per AGENTS.md "don't update deps without asking"
- **No LLM Wiki before this date** — this `wiki/` bootstraps the project's long-term memory (see [[ai-news-bot-architecture]])

## Relationships
- Pipeline components: [[ai-news-bot-architecture]]
- Resilience design: [[llm-provider-fallback]]
- Quality assurance: [[testing-strategy]]
- Remaining gaps: [[open-technical-debt]]

## Source References
- README.md (features, architecture, version history)
- PROGRESS.md (2026-07-04, 2026-07-12, 2026-08-20 sessions)
- `.hermes/repo-memory.md` (superseded; last updated 2026-07-12)
