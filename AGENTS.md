# AGENTS.md - AI News Bot

## Running the Bot

```bash
python main.py
```

Requires `.env` with:

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (required)
- At least one LLM API key: `GEMINI_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, or `GROQ_API_KEY`

Override fetch interval:

```bash
FETCH_INTERVAL_MINUTES=60 python main.py
```

## Testing

```bash
python test_apify.py      # Test Twitter/Reddit fetcher
python test_llm_providers.py  # Check LLM provider config
```

## Architecture

- `main.py` - Entry point, APScheduler (30-min intervals), pipeline orchestrator
- `config.py` - All settings via environment variables
- `modules/fetcher.py` - RSS, HN, ArXiv, GitHub fetching
- `modules/apify_fetcher.py` - Twitter (Nitter RSS) + Reddit JSON API
- `modules/llm.py` - Multi-provider LLM with automatic fallback
- `modules/dedup.py` - URL deduplication + keyword filtering
- `modules/sender.py` - Telegram delivery

Pipeline: fetch → dedup → keyword filter → LLM summarize → score filter → Telegram

## LLM Fallback System

Configured via `LLM_PROVIDER_ORDER` in `.env`. Default: `gemini,nvidia,openrouter,groq,ollama,lmstudio`. If primary fails, auto-falls back to next available provider.

## Key Env Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `MIN_RELEVANCE_SCORE` | 5 | Filter threshold |
| `BATCH_SIZE` | 3 | Articles per LLM call |
| `MAX_ARTICLES_PER_RUN` | 10 | Max to process |
| `ENABLE_RSS` | true | Toggle RSS feeds |
| `ENABLE_HN` | true | Toggle Hacker News |
| `ENABLE_ARXIV` | true | Toggle ArXiv |

## Gotchas

- `load_dotenv()` runs on `import config` - .env must be present or bot exits
- Twitter uses Nitter RSS (unreliable, often blocked); disable via `ENABLE_APIFY_TWITTER=false`
- Local LLMs (Ollama, LM Studio) require running servers on localhost
