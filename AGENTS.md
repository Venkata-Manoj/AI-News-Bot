# AGENTS.md - AI News Bot

## Running the Bot

```bash
# Single test run
python main.py

# Scheduled mode (runs every FETCH_INTERVAL_MINUTES)
python main.py --schedule

# Dry run (prints messages, doesn't send to Telegram)
python main.py --dry-run

# Fresh start (clears seen URL cache)
python main.py --fresh
```

Requires `.env` with:

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (required)
- At least one LLM API key: `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, or `GROQ_API_KEY`
- `YOUTUBE_API_KEY` (optional, for YouTube source)

## Testing

```bash
# Run all source tests
python tests/run_all_tests.py

# Run individual source tests
python tests/test_rss_feed.py
python tests/test_hn.py
python tests/test_arxiv.py
python tests/test_reddit.py
python tests/test_twitter.py
python tests/test_youtube.py
```

## Architecture

- `main.py` - Entry point, APScheduler, pipeline orchestrator
- `config.py` - All settings via environment variables
- `modules/fetcher.py` - RSS, HN, arXiv, YouTube, social source routing
- `modules/youtube_fetcher.py` - YouTube Data API v3 + yt-dlp transcripts
- `modules/apify_fetcher.py` - Twitter (Nitter RSS) + Reddit JSON API
- `modules/llm.py` - Multi-provider LLM with automatic fallback
- `modules/dedup.py` - URL deduplication + keyword filtering
- `modules/db.py` - SQLite state (seen URLs, YouTube videos, delivery log)
- `modules/formatter.py` - Telegram message formatting (article + YouTube)
- `modules/sender.py` - Telegram delivery with retry + proxy support
- `modules/dispatcher.py` - Async dispatch queue for low-latency delivery

Pipeline: fetch → dedup → keyword filter → LLM summarize → score filter → format → Telegram

## Sources

| Source | Config Flag | Notes |
|--------|------------|-------|
| RSS Feeds | `ENABLE_RSS` | 19+ AI blog feeds |
| Reddit | `ENABLE_APIFY_REDDIT` | Public JSON API, no key needed |
| Twitter | `ENABLE_APIFY_TWITTER` | Nitter RSS, unreliable |
| YouTube | `ENABLE_YOUTUBE` | Requires `YOUTUBE_API_KEY` |
| Hacker News | `ENABLE_HN` | Algolia API |
| arXiv | `ENABLE_ARXIV` | cs.AI, cs.LG, cs.CL |

## LLM Fallback System

Configured via `LLM_PROVIDER_ORDER` in `.env`.
Default: `gemini,nvidia,openrouter,groq,ollama,lmstudio`.
If primary fails (429/quota), auto-falls back to next available provider.

## Key Env Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `MIN_RELEVANCE_SCORE` | 6 | Filter threshold (1-10) |
| `BATCH_SIZE` | 5 | Articles per LLM call |
| `MAX_ARTICLES_PER_RUN` | 5 | Max to process per cycle |
| `FETCH_INTERVAL_MINUTES` | 45 | Scheduler interval |
| `YOUTUBE_MAX_VIDEOS_PER_CHANNEL` | 5 | Videos per channel per run |

## Gotchas

- `load_dotenv()` runs on `import config` — `.env` must be present
- Twitter uses Nitter RSS (unreliable, often blocked)
- Local LLMs (Ollama, LM Studio) require running servers
- `yt-dlp` must be installed for YouTube transcript downloads
- YouTube API free tier: 10,000 quota units/day
