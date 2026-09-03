---
title: LLM Provider Fallback
created: 2026-08-21
updated: 2026-08-21
type: concept
tags: [llm, architecture, module]
sources: [README.md, .hermes/repo-memory.md]
confidence: high
---

# LLM Provider Fallback Chain

AI-News-Bot summarizes and scores articles through a **6-provider fallback chain** so a single
provider outage or quota exhaustion never halts delivery. Order is configurable via
`LLM_PROVIDER_ORDER` (default `gemini,nvidia,openrouter,groq,ollama,lmstudio`).

## Chain (priority order)
| # | Provider | Model | Free tier |
|---|----------|-------|-----------|
| 1 | Google Gemini | gemini-2.5-flash | 1000 RPD |
| 2 | NVIDIA NIM | llama-3.3-nemotron-super-49b-v1 | Free |
| 3 | OpenRouter | gemma-4-31b-it:free | ~1000 RPD |
| 4 | Groq | llama-3.1-8b-instant | Fast free |
| 5 | Ollama | llama3.2:1b | Local |
| 6 | LM Studio | llama-3.1-8b-instruct | Local |

## Behavior
- On 429 / quota / transport failure, `llm.py` auto-falls back to the next available provider.
- `call_with_fallback` iterates `order`, skipping providers that are unavailable (no key) or
  absent from `_providers`, and on any exception (incl. `QUOTA_EXCEEDED`) advances to the next
  provider; returns `None` only when every provider fails or none are configured. Verified by
  `tests/unit/test_llm_fallback.py` (2026-08-29).
- `call_openrouter` / `call_groq` raise `QUOTA_EXCEEDED` on HTTP 429 and raise on any other
  non-200; `call_nvidia` retries on 429 (exponential backoff via `asyncio.sleep`) and raises on
  404 — **but see [[open-technical-debt]] #4**: 404 is currently swallowed inside its own loop.
- `parse_response` performs multi-stage JSON repair (clean array → dict-with-list → markdown
  fence → array extraction → first-level repair → last-resort object) so malformed LLM output
  still yields structured articles. See [[testing-strategy]] for the test suite validating this.
- At least one LLM key required (`GEMINI_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, or
  `GROQ_API_KEY`); local providers need running servers.
- `MIN_RELEVANCE_SCORE` (default 6/10) gates which summarized items are delivered.

## Related
- Module: [[ai-news-bot-architecture]] (llm.py)
- Quality: [[testing-strategy]]
- Project: [[ai-news-bot]]
