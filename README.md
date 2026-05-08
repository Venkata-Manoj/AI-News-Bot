# 🤖 AI News Bot

An autonomous AI news intelligence system that monitors **6 sources** (RSS, Reddit, Twitter, YouTube, Hacker News, arXiv), summarizes with **multi-provider LLM fallback**, and delivers curated updates to **Telegram**.

---

## ✨ Features

- **19 RSS feeds** — OpenAI, Anthropic, Google AI, DeepMind, Meta AI, HuggingFace, and more
- **Reddit** — r/MachineLearning, r/artificial, r/OpenAI, r/LocalLLaMA, r/singularity
- **YouTube** — 17 AI channels with transcript extraction, chunking, and top comments
- **Twitter** — Nitter RSS fallback (no API key needed)
- **Hacker News & arXiv** — Optional, disabled by default
- **6 LLM providers** — Gemini → NVIDIA → OpenRouter → Groq → Ollama → LM Studio
- **SQLite state** — Crash-proof dedup, delivery logs, YouTube video cache
- **Rich Telegram formatting** — Article summaries + YouTube cards with views, likes, comments

---

## 🚀 Quick Start

```bash
git clone https://github.com/Venkata-Manoj/AI-News-Bot.git
cd AI-News-Bot
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

### Required Keys

| Key | Where to get it |
|-----|----------------|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) (free, 1000 RPD) |

### Optional Keys

| Key | Purpose |
|-----|---------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 — [Google Cloud Console](https://console.cloud.google.com) |
| `NVIDIA_API_KEY` | LLM fallback — [NVIDIA NIM](https://build.nvidia.com) |
| `OPENROUTER_API_KEY` | LLM fallback — [OpenRouter](https://openrouter.ai) |
| `GROQ_API_KEY` | LLM fallback — [Groq](https://console.groq.com) |

---

## 📊 Architecture

```text
                     APScheduler (45 min interval)
                                │
          ┌──────────┬──────────┼──────────┬───────────┐
          ▼          ▼          ▼          ▼           ▼
       [RSS]     [Reddit]  [Twitter]  [YouTube]   [HN/arXiv]
       19 feeds  JSON API  Nitter     Data API    (disabled)
                                      + yt-dlp
          │          │         │          │
          └──────────┴─────────┴────┬─────┘
                                    ▼
                           SQLite Dedup +
                           Keyword Filter
                                    ▼
                            LLM Summarizer
                        (multi-provider fallback)
                                    ▼
                        Score Filter (≥6/10)
                                    ▼
                        Telegram Formatter
                             + Sender
```

---

## 🎬 YouTube Integration

The bot monitors **17 AI YouTube channels** with a full 4-stage pipeline:

1. **Resolve** — Channel handle → channel ID → uploads playlist
2. **Transcript** — Download & parse VTT subtitles via `yt-dlp` (with local caching)
3. **Chunk** — Split transcripts into 500-word chunks with timestamp URLs
4. **Comments** — Fetch top comments for social context

### YouTube Telegram Message

```text
🎬 DeepSeek V4 AI Beats Billion Dollar Systems…For Free
📺 Two Minute Papers

📝 DeepSeek V4 is a new open-source AI model with a 1M token
   context window that outperforms proprietary systems...

📊 131.0K views · 7.2K likes · 10m 4s
🏷️ #ai

💬 "What a Time To Be Alive" — @LordMannu (330 👍)

🔗 Watch: https://youtube.com/watch?v=p7K3xfViWCE
⏰ 19:30 IST | youtube
```

### Monitored Channels

`@AndrejKarpathy` `@TwoMinutePapers` `@YannicKilcher` `@lexfridman` `@sentdex` `@IBMTechnology` `@huggingface` `@freecodecamp` `@TinaHuang` `@okaashish` `@VarunMayya` `@rajshamani` `@AishwaryaSrinivasan` `@PrasadTechInTelugu` `@RawTalksWithVK` `@vibhavsishty`

---

## 🧠 LLM Fallback Chain

| Priority | Provider | Model | Free Tier |
|----------|----------|-------|-----------|
| 1 | Google Gemini | gemini-2.5-flash | 1000 RPD |
| 2 | NVIDIA NIM | llama-3.3-nemotron-super-49b-v1 | Free |
| 3 | OpenRouter | gemma-4-31b-it:free | ~1000 RPD |
| 4 | Groq | llama-3.1-8b-instant | Fast free |
| 5 | Ollama | llama3.2:1b | Local |
| 6 | LM Studio | llama-3.1-8b-instruct | Local |

Configure fallback order: `LLM_PROVIDER_ORDER=gemini,nvidia,openrouter,groq,ollama,lmstudio`

---

## 📁 Project Structure

```text
ai-news-bot/
├── main.py                    # Entry point + pipeline + scheduler
├── config.py                  # All settings via env vars
├── requirements.txt           # 11 dependencies
├── .env.example               # Config template
│
├── modules/
│   ├── fetcher.py             # Source router (RSS, HN, arXiv, YouTube)
│   ├── youtube_fetcher.py     # YouTube 4-stage pipeline
│   ├── apify_fetcher.py       # Twitter (Nitter) + Reddit (JSON API)
│   ├── llm.py                 # Multi-provider LLM with fallback
│   ├── dedup.py               # SQLite URL dedup + keyword filter
│   ├── db.py                  # SQLite state (7 tables)
│   ├── formatter.py           # Telegram formatting (article + YouTube)
│   ├── sender.py              # Telegram delivery with retry
│   └── dispatcher.py          # Async dispatch queue
│
├── tests/
│   ├── run_all_tests.py       # Master test runner
│   ├── test_rss_feed.py       # RSS validation
│   ├── test_hn.py             # Hacker News validation
│   ├── test_arxiv.py          # arXiv validation
│   ├── test_reddit.py         # Reddit validation
│   ├── test_twitter.py        # Twitter/Nitter validation
│   └── test_youtube.py        # YouTube full pipeline test
│
└── data/
    ├── bot.db                 # SQLite state database
    └── vtt/                   # Cached transcript files
```

---

## 🧪 Testing

```bash
# Run all source tests (no LLM calls, no Telegram sends)
python tests/run_all_tests.py

# Run individual tests
python tests/test_youtube.py
python tests/test_rss_feed.py
python tests/test_reddit.py
```

### Test Results (v3.0)

| Source | Status | Time |
|--------|--------|------|
| RSS Feeds | ✅ PASS | 2.2s |
| Hacker News | ❌ FAIL | 3.7s (disabled, expected) |
| arXiv | ✅ PASS | 1.1s |
| Reddit | ✅ PASS | 2.7s |
| Twitter/Nitter | ✅ PASS | 4.2s (0 tweets, Nitter blocked) |
| YouTube | ✅ PASS | 2.1s (all 4 stages) |

---

## ⚙️ Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `FETCH_INTERVAL_MINUTES` | 45 | Pipeline run interval |
| `MIN_RELEVANCE_SCORE` | 6 | LLM score threshold (1-10) |
| `BATCH_SIZE` | 5 | Articles per LLM call |
| `MAX_ARTICLES_PER_RUN` | 5 | Max articles per cycle |
| `YOUTUBE_MAX_VIDEOS_PER_CHANNEL` | 5 | Videos fetched per channel |
| `ENABLE_RSS` | true | Toggle RSS source |
| `ENABLE_YOUTUBE` | true | Toggle YouTube source |
| `ENABLE_APIFY_REDDIT` | true | Toggle Reddit source |

---

## 🏃 Running

```bash
# Single run
python main.py

# Scheduled mode
python main.py --schedule

# Dry run (no Telegram sends)
python main.py --dry-run

# Fresh start (clear dedup cache)
python main.py --fresh
```

---

## 📋 Version History

| Version | Date | Highlights |
|---------|------|------------|
| v1.0 | 2026-05-06 | RSS feeds, JSON dedup, Gemini, Telegram |
| v1.1 | 2026-05-06 | Added NVIDIA NIM, removed Reddit creds |
| v2.0 | 2026-05-06 | SQLite, async dispatcher, smart scheduler, LLM fallback |
| v2.1 | 2026-05-07 | Traffic optimization, reduced polling |
| **v3.0** | **2026-05-08** | **YouTube pipeline, yt-dlp transcripts, test suite, dead code cleanup** |
