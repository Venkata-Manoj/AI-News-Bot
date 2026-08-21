---
title: AI-News-Bot Architecture
created: 2026-08-21
updated: 2026-08-21
type: concept
tags: [architecture, pipeline, module, fetcher, llm, formatter, sender, dispatcher, db, dedup]
sources: [README.md, .hermes/repo-memory.md, AGENTS.md]
confidence: high
---

# Architecture (Pipeline)

AI-News-Bot is a single-process pipeline driven by APScheduler on a 45-minute interval.
Each cycle fetches from all enabled sources, normalizes, deduplicates, summarizes via LLM,
filters by relevance score, formats, and delivers to Telegram.

## Pipeline
```
APScheduler (FETCH_INTERVAL_MINUTES=45)
        │
   fetcher.py  ── source router: RSS(19 feeds), HN, arXiv, YouTube
   apify_fetcher.py ── Reddit (JSON API), Twitter (Nitter RSS)
        │
   dedup.py  ── SQLite URL dedup + keyword filter
        │
   llm.py  ── multi-provider summarize + score (see [[llm-provider-fallback]])
        │
   formatter.py  ── Telegram article cards + YouTube cards
        │
   dispatcher.py  ── async dispatch queue (batching, rate limit, retry)
        │
   sender.py  ── Telegram delivery (retry + proxy support)
   db.py  ── SQLite state: seen_urls, daily_calls, source_state,
                      error_log, delivery_log, youtube_videos, youtube_comments
```

## Modules
| Module | Role | Tests |
|--------|------|-------|
| config.py | Env-var config (load_dotenv on import) | N/A |
| fetcher.py | RSS/HN/arXiv/YouTube routing | indirect (source tests) |
| apify_fetcher.py | Reddit + Twitter | indirect |
| youtube_fetcher.py | YouTube 4-stage pipeline (resolve→transcript→chunk→comments) | unit (test_youtube_utils.py) |
| dedup.py | URL dedup + keyword filter | test_dedup.py (21) |
| llm.py | LLM call + JSON-repair + scoring | unit (test_llm_parse.py) |
| formatter.py | Telegram markdown formatting | test_formatter.py (70) |
| dispatcher.py | Async batching queue | unit (test_dispatcher_unit.py) |
| sender.py | Telegram HTTP send + retry | test_sender.py (17) |
| db.py | SQLite 7-table state | test_db.py (28) |

## Gotchas (from AGENTS.md)
- `load_dotenv()` runs on `import config` — `.env` MUST be present
- Twitter/Nitter RSS is unreliable (often blocked)
- `yt-dlp` required for YouTube transcripts; YouTube API free tier = 10k quota units/day
- YouTube format path previously had a latent `async` bug (fixed 2026-07-12)

## Related
- Resilience: [[llm-provider-fallback]]
- Verification: [[testing-strategy]]
- Gaps: [[open-technical-debt]]
- Project entity: [[ai-news-bot]]
