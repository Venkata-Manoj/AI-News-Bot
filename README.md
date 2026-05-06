# AI Intelligence Bot

Zero-cost, autonomous AI news intelligence system that fetches, filters, summarizes and delivers to Telegram.

## Quick Start

```bash
git clone https://github.com/yourusername/ai-news-bot.git
cd ai-news-bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
python main.py
```

## Multi-Provider Support

Configure **at least one** LLM provider in `.env`:

| Provider | API Key | Free Limit | Setup |
|----------|--------|------------|-------|
| **Gemini** | `GEMINI_API_KEY` | 1000 RPD | [Google AI Studio](https://aistudio.google.com) |
| **OpenRouter** | `OPENROUTER_API_KEY` | ~1000 RPD | [OpenRouter](https://openrouter.ai) |
| **Groq** | `GROQ_API_KEY` | Fast tier | [Groq](https://console.groq.com) |
| **Ollama** | (local) | Unlimited | [Ollama](https://ollama.com) |
| **LM Studio** | (local) | Unlimited | [LM Studio](https://lmstudio.ai) |

### Fallback Order

Set `LLM_PROVIDER_ORDER` to control priority:
```bash
LLM_PROVIDER_ORDER=gemini,openrouter,groq,ollama,lmstudio
```

If Gemini fails, it auto-falls back to OpenRouter, then Groq, etc.

## Sources

- 10 RSS feeds (OpenAI, Google AI, HuggingFace, TechCrunch, etc.)
- 4 Reddit subreddits (r/MachineLearning, r/OpenAI, etc.)

## Architecture

```
APScheduler (30-min)
     ↓
RSS + Reddit fetcher
     ↓
Dedup + Keyword filter
     ↓
LLM (Gemini/OpenRouter/Groq/Ollama)
     ↓
Score filter + Format
     ↓
Telegram (3s rate limit)
```

## Files

```
ai-news-bot/
├── main.py           # Pipeline + scheduler
├── config.py         # Configuration
├── modules/
│   ├── fetcher.py   # RSS + Reddit
│   ├── dedup.py     # URL dedup
│   ├── llm.py      # Multi-provider LLM
│   ├── formatter.py # MarkdownV2
│   └── sender.py   # Telegram
├── data/
│   └── seen_urls.json
└── .env
```

## Run

```bash
python main.py
```

Runs every 30 minutes. Override:
```bash
FETCH_INTERVAL_MINUTES=60 python main.py
```

## License

MIT