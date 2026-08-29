"""Unit tests for the LLM provider fallback orchestration in modules/llm.py.

These tests cover the *resilience* logic that the existing test_llm_parse.py
pure-path suite does not:

  - call_with_fallback   — order iteration, unavailable-provider skipping,
                           quota/error fall-through, all-fail -> None
  - call_openrouter      — 200 success, 429 quota raise, non-200 raise
  - call_groq            — 200 success, 429 quota raise
  - call_nvidia          — 200 success, 404 raise, 429 retry-then-None

No network, no API keys. httpx.AsyncClient is replaced with an in-memory
fake, and increment_daily_calls is stubbed so no SQLite side effects occur.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

import modules.llm as llm


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


class FakeAsyncClient:
    """Stand-in for httpx.AsyncClient returning scripted responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        self.post_calls.append((url, headers, json))
        return self._responses.pop(0)


# Real provider endpoints per init_providers() — used so the "posts to the
# correct endpoint" assertions validate the configured URL, not a dummy.
_REAL_ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
}


def provider(name: str, endpoint: str = None) -> llm.LLMProvider:
    """Available provider with a fake API key + (real) endpoint."""
    return llm.LLMProvider(name, "fake-key", endpoint=endpoint or _REAL_ENDPOINTS.get(name, "https://example.test/v1"))


# --------------------------------------------------------------------------- #
# call_with_fallback orchestration
# --------------------------------------------------------------------------- #
class TestCallWithFallback:
    def test_returns_first_available_result(self, monkeypatch):
        monkeypatch.setattr(
            llm,
            "_providers",
            {"gemini": provider("gemini"), "groq": provider("groq")},
        )
        gem = AsyncMock(return_value="gemini-result")
        groq = AsyncMock(return_value="groq-result")
        monkeypatch.setattr(
            llm, "_PROVIDER_FUNCTIONS",
            {"gemini": gem, "groq": groq},
        )

        out = asyncio.run(llm.call_with_fallback("prompt", ["gemini", "groq"]))
        assert out == "gemini-result"
        gem.assert_awaited_once()
        groq.assert_not_awaited()

    def test_falls_through_on_generic_exception(self, monkeypatch):
        monkeypatch.setattr(
            llm, "_providers",
            {"gemini": provider("gemini"), "groq": provider("groq")},
        )
        gem = AsyncMock(side_effect=RuntimeError("boom"))
        groq = AsyncMock(return_value="recovered")
        monkeypatch.setattr(
            llm, "_PROVIDER_FUNCTIONS",
            {"gemini": gem, "groq": groq},
        )

        out = asyncio.run(llm.call_with_fallback("prompt", ["gemini", "groq"]))
        assert out == "recovered"

    def test_quota_error_triggers_fallback(self, monkeypatch):
        monkeypatch.setattr(
            llm, "_providers",
            {"gemini": provider("gemini"), "groq": provider("groq")},
        )
        gem = AsyncMock(side_effect=Exception("QUOTA_EXCEEDED: 429 rate limit"))
        groq = AsyncMock(return_value="after-quota")
        monkeypatch.setattr(
            llm, "_PROVIDER_FUNCTIONS",
            {"gemini": gem, "groq": groq},
        )

        out = asyncio.run(llm.call_with_fallback("prompt", ["gemini", "groq"]))
        assert out == "after-quota"

    def test_skips_unavailable_provider(self, monkeypatch):
        # gemini present but not available (empty key); groq available
        monkeypatch.setattr(
            llm, "_providers",
            {"gemini": llm.LLMProvider("gemini", ""), "groq": provider("groq")},
        )
        groq = AsyncMock(return_value="groq-only")
        monkeypatch.setattr(llm, "_PROVIDER_FUNCTIONS", {"groq": groq})

        out = asyncio.run(llm.call_with_fallback("prompt", ["gemini", "groq"]))
        assert out == "groq-only"

    def test_unknown_provider_in_order_skipped(self, monkeypatch):
        monkeypatch.setattr(llm, "_providers", {"groq": provider("groq")})
        groq = AsyncMock(return_value="ok")
        # _PROVIDER_FUNCTIONS lacks "bogus" -> must be skipped without error
        monkeypatch.setattr(llm, "_PROVIDER_FUNCTIONS", {"groq": groq})

        out = asyncio.run(llm.call_with_fallback("prompt", ["bogus", "groq"]))
        assert out == "ok"

    def test_falsy_result_falls_through(self, monkeypatch):
        # empty string is falsy -> fallback continues to next provider
        monkeypatch.setattr(
            llm, "_providers",
            {"gemini": provider("gemini"), "groq": provider("groq")},
        )
        gem = AsyncMock(return_value="")
        groq = AsyncMock(return_value="real")
        monkeypatch.setattr(
            llm, "_PROVIDER_FUNCTIONS",
            {"gemini": gem, "groq": groq},
        )

        out = asyncio.run(llm.call_with_fallback("prompt", ["gemini", "groq"]))
        assert out == "real"

    def test_returns_none_when_all_fail(self, monkeypatch):
        monkeypatch.setattr(
            llm, "_providers",
            {"gemini": provider("gemini"), "groq": provider("groq")},
        )
        gem = AsyncMock(side_effect=Exception("err1"))
        groq = AsyncMock(side_effect=Exception("err2"))
        monkeypatch.setattr(
            llm, "_PROVIDER_FUNCTIONS",
            {"gemini": gem, "groq": groq},
        )

        out = asyncio.run(llm.call_with_fallback("prompt", ["gemini", "groq"]))
        assert out is None

    def test_returns_none_when_no_providers(self, monkeypatch):
        monkeypatch.setattr(llm, "_providers", {})
        monkeypatch.setattr(llm, "_PROVIDER_FUNCTIONS", {})

        out = asyncio.run(llm.call_with_fallback("prompt"))
        assert out is None


# --------------------------------------------------------------------------- #
# Per-provider HTTP handlers (httpx mocked)
# --------------------------------------------------------------------------- #
def _patch_http(monkeypatch, responses, provider_name="openrouter"):
    monkeypatch.setattr(
        llm, "_providers", {provider_name: provider(provider_name)}
    )
    monkeypatch.setattr(llm, "increment_daily_calls", lambda *a, **k: None)
    client = FakeAsyncClient(responses)
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda *a, **k: client)
    return client


class TestOpenRouter:
    def test_success_returns_content(self, monkeypatch):
        resp = FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "hello"}}]},
        )
        client = _patch_http(monkeypatch, [resp], "openrouter")

        out = asyncio.run(llm.call_openrouter("prompt"))
        assert out == "hello"
        assert client.post_calls[0][0] == "https://openrouter.ai/api/v1/chat/completions"

    def test_429_raises_quota(self, monkeypatch):
        _patch_http(monkeypatch, [FakeResponse(status_code=429, text="slow")], "openrouter")
        try:
            asyncio.run(llm.call_openrouter("prompt"))
            pytest.fail("expected QUOTA exception")
        except Exception as e:
            assert "QUOTA_EXCEEDED" in str(e)

    def test_non_200_raises(self, monkeypatch):
        _patch_http(monkeypatch, [FakeResponse(status_code=500, text="oops")], "openrouter")
        try:
            asyncio.run(llm.call_openrouter("prompt"))
            pytest.fail("expected error")
        except Exception as e:
            assert "OpenRouter error" in str(e)


class TestGroq:
    def test_success_returns_content(self, monkeypatch):
        resp = FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "groq-says"}}]},
        )
        client = _patch_http(monkeypatch, [resp], "groq")

        out = asyncio.run(llm.call_groq("prompt"))
        assert out == "groq-says"
        assert client.post_calls[0][0] == "https://api.groq.com/openai/v1/chat/completions"

    def test_429_raises_quota(self, monkeypatch):
        _patch_http(monkeypatch, [FakeResponse(status_code=429, text="rl")], "groq")
        try:
            asyncio.run(llm.call_groq("prompt"))
            pytest.fail("expected QUOTA exception")
        except Exception as e:
            assert "QUOTA_EXCEEDED" in str(e)


class TestNvidia:
    def test_success_returns_content(self, monkeypatch):
        resp = FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "nvidia-ok"}}]},
        )
        client = _patch_http(monkeypatch, [resp], "nvidia")

        out = asyncio.run(llm.call_nvidia("prompt"))
        assert out == "nvidia-ok"
        assert client.post_calls[0][0] == "https://integrate.api.nvidia.com/v1/chat/completions"

    @pytest.mark.xfail(
        reason=(
            "LATENT BUG: call_nvidia raises the 404 inside its own try/except "
            "loop and swallows it, returning None. Per the dispatch contract a "
            "hard 404 (model not found) should propagate so fallback attempts the "
            "next provider instead of silently giving up. Flip to pass (remove "
            "xfail) once call_nvidia no longer swallows 4xx raises."
        ),
        strict=True,
    )
    def test_404_raises(self, monkeypatch):
        _patch_http(monkeypatch, [FakeResponse(status_code=404, text="nf")], "nvidia")
        try:
            out = asyncio.run(llm.call_nvidia("prompt"))
            pytest.fail(f"expected 404 to propagate, got: {out!r}")
        except Exception as e:
            assert "404" in str(e)

    def test_429_retries_then_returns_none(self, monkeypatch):
        # All attempts rate-limited -> retries exhausted -> None (no hang)
        monkeypatch.setattr(llm.asyncio, "sleep", AsyncMock())
        _patch_http(
            monkeypatch,
            [FakeResponse(status_code=429, text="rl")] * 3,
            "nvidia",
        )
        out = asyncio.run(llm.call_nvidia("prompt", retries=3))
        assert out is None

    def test_429_then_success_returns_content(self, monkeypatch):
        monkeypatch.setattr(llm.asyncio, "sleep", AsyncMock())
        ok = FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": "after-retry"}}]},
        )
        _patch_http(monkeypatch, [FakeResponse(status_code=429, text="rl"), ok], "nvidia")
        out = asyncio.run(llm.call_nvidia("prompt", retries=3))
        assert out == "after-retry"
