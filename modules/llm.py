import json
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from enum import Enum

import aiohttp
import httpx

import config


class Provider(Enum):
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    LOCAL = "local"


class LLMProvider:
    def __init__(
        self, name: str, api_key: str, endpoint: str = None, model: str = None
    ):
        self.name = name
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model or "default"
        self.available = bool(api_key)

    def __repr__(self):
        return (
            f"<LLMProvider {self.name} model={self.model} available={self.available}>"
        )


_providers: Dict[str, LLMProvider] = {}


def init_providers():
    _providers.clear()

    if config.GEMINI_API_KEY:
        _providers["gemini"] = LLMProvider(
            "gemini",
            config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL or "gemini-2.5-flash-lite-preview-06-17",
        )

    if config.OPENROUTER_API_KEY:
        _providers["openrouter"] = LLMProvider(
            "openrouter",
            config.OPENROUTER_API_KEY,
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            model=config.OPENROUTER_MODEL or "google/gemini-2.5-flash-lite:free",
        )

    if config.GROQ_API_KEY:
        _providers["groq"] = LLMProvider(
            "groq",
            config.GROQ_API_KEY,
            endpoint="https://api.groq.com/openai/v1/chat/completions",
            model=config.GROQ_MODEL or "llama-3.1-8b-instant",
        )

    if config.NVIDIA_API_KEY:
        _providers["nvidia"] = LLMProvider(
            "nvidia",
            config.NVIDIA_API_KEY,
            endpoint="https://integrate.api.nvidia.com/v1/chat/completions",
            model=config.NVIDIA_MODEL or "nvidia/llama-3.1-nemotron-70b-instruct",
        )

    if config.OLLAMA_ENDPOINT:
        _providers["ollama"] = LLMProvider(
            "ollama",
            config.OLLAMA_ENDPOINT,
            endpoint=f"{config.OLLAMA_ENDPOINT}/api/chat",
            model=config.OLLAMA_MODEL or "llama3.1",
        )

    if config.LMSTUDIO_ENDPOINT:
        _providers["lmstudio"] = LLMProvider(
            "lmstudio",
            "local",
            endpoint=f"{config.LMSTUDIO_ENDPOINT}/v1/chat/completions",
            model=config.LMSTUDIO_MODEL or "llama-3.1-8b-instruct",
        )

    return _providers


def get_provider(order: List[str] = None) -> Optional[LLMProvider]:
    if order is None:
        order = ["gemini", "openrouter", "groq", "ollama", "lmstudio"]

    for name in order:
        if name in _providers and _providers[name].available:
            return _providers[name]

    return None


SYSTEM_PROMPT = """You are a concise AI news editor. For each article below, output ONLY a JSON array. Each element must have: 'index' (int), 'summary' (2 sentences, plain English, 8th grade level), 'score' (int 1–10, where 10 = highly relevant AI news, 1 = off-topic). No markdown, no explanation, just the array."""


def build_prompt(articles) -> str:
    user_parts = []
    for i, article in enumerate(articles, 1):
        body_snippet = article.body[:400] if article.body else "(no body available)"
        user_parts.append(f"[{i}] {article.title}\n{body_snippet}")

    return "\n\n".join(user_parts)


async def call_gemini(prompt: str, retries: int = 3) -> Optional[str]:
    import google.generativeai as genai

    provider = _providers.get("gemini")
    if not provider or not provider.available:
        return None

    genai.configure(api_key=provider.api_key)
    model = genai.GenerativeModel(provider.model)

    for attempt in range(retries):
        try:
            response = model.generate_content(
                [SYSTEM_PROMPT, prompt],
                generation_config={"temperature": 0.3, "max_output_tokens": 2048},
            )
            increment_daily_calls(1)
            return response.text
        except Exception as e:
            print(f"[Gemini] Error (attempt {attempt + 1}): {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                await asyncio.sleep(12 * (2**attempt))
            else:
                break

    return None


async def call_openrouter(prompt: str, retries: int = 3) -> Optional[str]:
    provider = _providers.get("openrouter")
    if not provider or not provider.available:
        return None

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    provider.endpoint, headers=headers, json=payload
                )

                if resp.status_code == 200:
                    data = resp.json()
                    increment_daily_calls(1)
                    return data["choices"][0]["message"]["content"]
                elif resp.status_code == 429:
                    print(f"[OpenRouter] Rate limited, retry {attempt + 1}")
                    wait_time = 12 * (2**attempt)
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[OpenRouter] Error: {resp.status_code} - {resp.text[:100]}")
                    break
        except asyncio.CancelledError:
            print(f"[OpenRouter] Interrupted, skipping")
            raise
        except Exception as e:
            print(f"[OpenRouter] Error (attempt {attempt + 1}): {e}")

    return None


async def call_groq(prompt: str, retries: int = 3) -> Optional[str]:
    provider = _providers.get("groq")
    if not provider or not provider.available:
        return None

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    provider.endpoint, headers=headers, json=payload
                )

                if resp.status_code == 200:
                    data = resp.json()
                    increment_daily_calls(1)
                    return data["choices"][0]["message"]["content"]
                elif resp.status_code == 429:
                    print(f"[Groq] Rate limited, retry {attempt + 1}")
                    wait_time = 12 * (2**attempt)
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[Groq] Error: {resp.status_code}")
                    break
        except asyncio.CancelledError:
            print(f"[Groq] Interrupted, skipping")
            raise
        except Exception as e:
            print(f"[Groq] Error (attempt {attempt + 1}): {e}")

    return None


async def call_nvidia(prompt: str, retries: int = 3) -> Optional[str]:
    provider = _providers.get("nvidia")
    if not provider or not provider.available:
        return None

    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    provider.endpoint, headers=headers, json=payload
                )

                if resp.status_code == 200:
                    data = resp.json()
                    increment_daily_calls(1)
                    return data["choices"][0]["message"]["content"]
                elif resp.status_code == 429:
                    print(f"[NVIDIA] Rate limited, retry {attempt + 1}")
                    wait_time = 12 * (2**attempt)
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[NVIDIA] Error: {resp.status_code} - {resp.text[:100]}")
                    break
        except asyncio.CancelledError:
            print(f"[NVIDIA] Interrupted, skipping")
            raise
        except Exception as e:
            print(f"[NVIDIA] Error (attempt {attempt + 1}): {e}")

    return None


async def call_ollama(prompt: str, retries: int = 3) -> Optional[str]:
    provider = _providers.get("ollama")
    if not provider or not provider.available:
        return None

    payload = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "stream": False,
    }

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(provider.endpoint, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    increment_daily_calls(1)
                    return data["message"]["content"]
                else:
                    print(f"[Ollama] Error: {resp.status_code}")
        except Exception as e:
            print(f"[Ollama] Error (attempt {attempt + 1}): {e}")

    return None


async def call_lmstudio(prompt: str, retries: int = 3) -> Optional[str]:
    provider = _providers.get("lmstudio")
    if not provider or not provider.available:
        return None

    headers = {"Content-Type": "application/json"}

    payload = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    provider.endpoint, headers=headers, json=payload
                )

                if resp.status_code == 200:
                    data = resp.json()
                    increment_daily_calls(1)
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"[LMStudio] Error: {resp.status_code}")
        except Exception as e:
            print(f"[LMStudio] Error (attempt {attempt + 1}): {e}")

    return None


_PROVIDER_FUNCTIONS = {
    "gemini": call_gemini,
    "openrouter": call_openrouter,
    "groq": call_groq,
    "nvidia": call_nvidia,
    "ollama": call_ollama,
    "lmstudio": call_lmstudio,
}


async def call_with_fallback(prompt: str, order: List[str] = None) -> Optional[str]:
    if order is None:
        order = ["gemini", "nvidia", "openrouter", "groq", "ollama", "lmstudio"]

    last_error = None
    for provider_name in order:
        if provider_name in _PROVIDER_FUNCTIONS:
            print(f"[LLM] Trying {provider_name}...")
            try:
                func = _PROVIDER_FUNCTIONS[provider_name]
                result = await func(prompt)
                if result:
                    return result
            except asyncio.CancelledError:
                print(f"[LLM] {provider_name} interrupted")
                raise
            except Exception as e:
                last_error = e
                print(f"[LLM] {provider_name} failed: {e}")

    print(f"[LLM] All providers failed. Last error: {last_error}")
    return None


def parse_response(text: str) -> List[Dict]:
    text = text.strip()

    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    import re

    pattern = r"\[\s*\{.*?\}\s*\]"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass

    print("[LLM] Failed to parse JSON response")
    return []


def load_daily_calls() -> dict:
    try:
        with open(config.DAILY_CALLS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"count": 0, "date": ""}


def save_daily_calls(data: dict):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.DAILY_CALLS_FILE, "w") as f:
        json.dump(data, f)


def get_daily_call_count() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = load_daily_calls()

    if data.get("date") != today:
        data = {"count": 0, "date": today}
        save_daily_calls(data)
        return 0

    return data.get("count", 0)


def increment_daily_calls(count: int = 1):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data = load_daily_calls()

    if data.get("date") != today:
        data = {"count": 0, "date": today}

    data["count"] = data.get("count", 0) + count
    save_daily_calls(data)


async def summarise_batch_flex(articles, order: List[str] = None) -> List[Dict]:
    if not articles:
        return []

    prompt = build_prompt(articles)
    response_text = await call_with_fallback(prompt, order)

    if not response_text:
        return []

    results = parse_response(response_text)

    results_dict = {r["index"]: r for r in results if "index" in r}

    summaries = []
    for i, article in enumerate(articles, 1):
        if i in results_dict:
            summary_data = results_dict[i]
            summaries.append(
                {
                    "article": article,
                    "summary": summary_data.get("summary", article.title),
                    "score": summary_data.get("score", 5),
                }
            )

    return summaries


async def summarise_all_flex(
    articles, order: List[str] = None, batch_size: int = None
) -> List[Dict]:
    if batch_size is None:
        batch_size = config.BATCH_SIZE

    all_summaries = []

    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]

        if get_daily_call_count() >= 950:
            print("[LLM] Daily limit reached, skipping remaining batches")
            break

        print(f"[LLM] Processing batch {i // batch_size + 1} ({len(batch)} articles)")
        batch_results = await summarise_batch_flex(batch, order)
        all_summaries.extend(batch_results)

        await asyncio.sleep(1)

    print(f"[LLM] Total summaries: {len(all_summaries)}")
    return all_summaries


def filter_by_score(summaries: List[Dict], min_score: int = None) -> List[Dict]:
    if min_score is None:
        min_score = config.MIN_RELEVANCE_SCORE

    filtered = [s for s in summaries if s.get("score", 0) >= min_score]

    print(
        f"[Filter] {len(filtered)} passed score {min_score}+ of {len(summaries)} total"
    )
    return filtered
