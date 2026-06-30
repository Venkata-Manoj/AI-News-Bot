import asyncio
import json
from datetime import UTC, datetime
from enum import Enum

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


_providers: dict[str, LLMProvider] = {}


def init_providers():
    _providers.clear()

    if config.GEMINI_API_KEY:
        _providers["gemini"] = LLMProvider(
            "gemini",
            config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL or "gemini-2.5-flash",
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
            model=config.NVIDIA_MODEL or "nvidia/llama-3.3-nemotron-super-49b-v1",
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


def get_provider(order: list[str] = None) -> LLMProvider | None:
    if order is None:
        order = ["gemini", "openrouter", "groq", "ollama", "lmstudio"]

    for name in order:
        if name in _providers and _providers[name].available:
            return _providers[name]

    return None


SYSTEM_PROMPT = """You are a concise AI news editor. For each article, return ONLY a valid JSON array.
Each element must be a JSON object with exactly these keys:
- "index": integer matching the article number
- "summary": 2-sentence plain English summary
- "score": integer 1-10 (10 = highly relevant AI news)

Example output for 2 articles:
[{"index": 1, "summary": "Summary here.", "score": 8}, {"index": 2, "summary": "Summary here.", "score": 6}]

Return ONLY the JSON array. No markdown, no explanation, no extra text."""


def build_prompt(articles) -> str:
    user_parts = []
    for i, article in enumerate(articles, 1):
        body_snippet = article.body[:400] if article.body else "(no body available)"
        user_parts.append(f"[{i}] {article.title}\n{body_snippet}")

    return "\n\n".join(user_parts)


async def call_gemini(prompt: str, retries: int = 1) -> str | None:
    """Call Gemini - on quota error, raise immediately so fallback can try next provider."""
    import google.generativeai as genai

    provider = _providers.get("gemini")
    if not provider or not provider.available:
        return None

    genai.configure(api_key=provider.api_key)
    model = genai.GenerativeModel(provider.model)

    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, prompt],
            generation_config={"temperature": 0.3, "max_output_tokens": 2048},
        )
        increment_daily_calls(1)
        return response.text
    except Exception as e:
        error_str = str(e)
        print(f"[Gemini] Error: {error_str[:100]}...")
        # Immediately raise on quota errors so fallback can work
        if (
            "429" in error_str
            or "quota" in error_str.lower()
            or "rate limit" in error_str.lower()
        ):
            raise Exception(f"QUOTA_EXCEEDED: {error_str}") from e
        return None


async def call_openrouter(prompt: str) -> str | None:
    """Call OpenRouter - on any error, raise so fallback works."""
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
                raise Exception("QUOTA_EXCEEDED: OpenRouter rate limited")
            else:
                raise Exception(f"OpenRouter error: {resp.status_code} - {resp.text[:100]}")
    except asyncio.CancelledError:
        raise


async def call_groq(prompt: str) -> str | None:
    """Call Groq - on any error, raise so fallback works."""
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
                raise Exception("QUOTA_EXCEEDED: Groq rate limited")
            else:
                raise Exception(f"Groq error: {resp.status_code}")
    except asyncio.CancelledError:
        raise


async def call_nvidia(prompt: str, retries: int = 3) -> str | None:
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
                elif resp.status_code == 404:
                    raise Exception(f"NVIDIA model not found (404): {resp.text[:100]}")
                else:
                    print(f"[NVIDIA] Error: {resp.status_code} - {resp.text[:100]}")
                    break
        except asyncio.CancelledError:
            print("[NVIDIA] Interrupted, skipping")
            raise
        except Exception as e:
            print(f"[NVIDIA] Error (attempt {attempt + 1}): {e}")

    return None


async def call_ollama(prompt: str, retries: int = 3) -> str | None:
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


async def call_lmstudio(prompt: str, retries: int = 3) -> str | None:
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


async def call_with_fallback(prompt: str, order: list[str] = None) -> str | None:
    if order is None:
        order = ["gemini", "nvidia", "openrouter", "groq", "ollama", "lmstudio"]

    last_error = None
    for provider_name in order:
        if provider_name not in _PROVIDER_FUNCTIONS:
            continue

        provider = _providers.get(provider_name)
        if not provider or not provider.available:
            print(f"[LLM] {provider_name} not available (no API key)")
            continue

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
            error_str = str(e)
            last_error = e

            # Check for quota errors (429) - immediately try next provider
            if (
                "429" in error_str
                or "quota" in error_str.lower()
                or "rate limit" in error_str.lower()
                or "QUOTA_EXCEEDED" in error_str
            ):
                print(f"[LLM] {provider_name} quota exceeded, trying next provider...")
                continue

            print(f"[LLM] {provider_name} failed: {e}")

    print(f"[LLM] All providers failed. Last error: {last_error}")
    return None


def parse_response(text: str) -> list[dict]:
    if not text:
        return []

    original = text
    text = text.strip()

    # 1. Strip <think>...</think> reasoning blocks (Nemotron, DeepSeek, etc.)
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Extract from markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # 3. Try direct JSON parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        # If it returned a dict with a list inside, try to extract
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError:
        pass

    # 4. Find JSON array anywhere in the text (greedy)
    array_match = re.search(r"\[[\s\S]*\]", text)
    if array_match:
        try:
            parsed = json.loads(array_match.group())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # 5. Try to repair malformed output: ["index":1,"summary":"...","score":9,"index":2,...]
    # Some models omit {} around objects — reconstruct them
    if '"index"' in text and '"score"' in text:
        try:
            # Split on "index" boundaries and wrap each chunk in {}
            chunks = re.split(r',?\s*"index"\s*:', text)
            results = []
            for chunk in chunks:
                chunk = chunk.strip().strip('[').strip(']').strip(',')
                if not chunk:
                    continue
                obj_str = '{"index":' + chunk + '}'
                # Clean trailing junk
                obj_str = re.sub(r',\s*}', '}', obj_str)
                try:
                    obj = json.loads(obj_str)
                    if 'index' in obj:
                        results.append(obj)
                except json.JSONDecodeError:
                    continue
            if results:
                print(f"[LLM] Repaired {len(results)} objects from malformed response")
                return results
        except Exception:
            pass

    # 6. Last resort: find individual JSON objects
    obj_matches = re.findall(r"\{[^{}]*\}", text)
    if obj_matches:
        results = []
        for obj_str in obj_matches:
            try:
                obj = json.loads(obj_str)
                if "index" in obj or "summary" in obj:
                    results.append(obj)
            except json.JSONDecodeError:
                continue
        if results:
            return results

    # Debug: show what we got so we can diagnose
    print(f"[LLM] Failed to parse JSON response. Raw ({len(original)} chars):")
    print(f"[LLM] >>> {original[:500]}{'...' if len(original) > 500 else ''}")
    return []


def load_daily_calls() -> dict:
    """Load daily call count from SQLite (replacing old JSON)."""
    from modules.db import db

    return {
        "count": db.get_daily_call_count(),
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


def save_daily_calls(data: dict):
    """Save daily call count to SQLite (replacing old JSON)."""
    pass  # Handled by SQLite now


def get_daily_call_count() -> int:
    from modules.db import db

    return db.get_daily_call_count()


def increment_daily_calls(count: int = 1):
    """Track LLM call in SQLite."""
    from modules.db import db

    db.increment_daily_calls(count)


async def summarise_batch_flex(articles, order: list[str] = None) -> list[dict]:
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
    articles, order: list[str] = None, batch_size: int = None
) -> list[dict]:
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


def filter_by_score(summaries: list[dict], min_score: int = None) -> list[dict]:
    if min_score is None:
        min_score = config.MIN_RELEVANCE_SCORE

    filtered = [s for s in summaries if s.get("score", 0) >= min_score]

    print(
        f"[Filter] {len(filtered)} passed score {min_score}+ of {len(summaries)} total"
    )
    return filtered
