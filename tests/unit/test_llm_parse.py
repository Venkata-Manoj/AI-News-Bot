"""Unit tests for modules/llm.py — pure, deterministic functions.

Focus: ``parse_response`` (multi-stage JSON-repair), ``build_prompt``,
``filter_by_score``, ``summarise_batch_flex`` (provider mocked), and provider
selection. No network, no API keys required.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import AsyncMock

import pytest

import modules.llm as llm


def make_article(title="T", body="B", source="rss"):
    """Minimal article-like object for prompt/summarise tests."""

    class FakeArticle:
        def __init__(self, t, b, s):
            self.title = t
            self.body = b
            self.source = s
            self.url = "https://example.com/article"
            self.url_hash = "h"

    return FakeArticle(title, body, source)


class TestParseResponse:
    def test_none_returns_empty(self):
        assert llm.parse_response(None) == []  # type: ignore[arg-type]

    def test_empty_string(self):
        assert llm.parse_response("") == []

    def test_clean_json_array(self):
        text = (
            '[{"index":1,"summary":"S1","score":8},'
            '{"index":2,"summary":"S2","score":6}]'
        )
        assert llm.parse_response(text) == [
            {"index": 1, "summary": "S1", "score": 8},
            {"index": 2, "summary": "S2", "score": 6},
        ]

    def test_dict_with_inner_list(self):
        text = '{"results":[{"index":1,"summary":"S1","score":9}]}'
        assert llm.parse_response(text) == [{"index": 1, "summary": "S1", "score": 9}]

    def test_markdown_fence_json(self):
        text = "```json\n[{\"index\":1,\"summary\":\"S\",\"score\":7}]\n```"
        out = llm.parse_response(text)
        assert out[0]["index"] == 1

    def test_array_extracted_from_surrounding_text(self):
        text = "Here are the results: [{\"index\":1,\"summary\":\"S\",\"score\":8}] hope that helps"
        assert llm.parse_response(text)[0]["index"] == 1

    def test_malformed_first_level_repair(self):
        # Model omitted the {} around each object
        text = '["index":1,"summary":"S1","score":9,"index":2,"summary":"S2","score":4]'
        out = llm.parse_response(text)
        assert {"index": 1, "summary": "S1", "score": 9} in out
        assert {"index": 2, "summary": "S2", "score": 4} in out

    def test_last_resort_object_extraction(self):
        text = 'garbage {"index":3,"summary":"x","score":6} more garbage'
        out = llm.parse_response(text)
        assert any(o.get("index") == 3 for o in out)

    def test_unparseable_returns_empty(self):
        assert llm.parse_response("no json here at all !!") == []


class TestBuildPrompt:
    def test_includes_title_and_body_and_index(self):
        arts = [make_article("Title A", "Body A"), make_article("Title B", "Body B")]
        prompt = llm.build_prompt(arts)
        assert "[1] Title A" in prompt
        assert "Body A" in prompt
        assert "[2] Title B" in prompt

    def test_body_truncated_to_400(self):
        long_body = "x" * 1000
        prompt = llm.build_prompt([make_article("T", long_body)])
        assert "x" * 400 in prompt
        assert "x" * 401 not in prompt

    def test_missing_body_placeholder(self):
        prompt = llm.build_prompt([make_article("T", "")])
        assert "(no body available)" in prompt


class TestFilterByScore:
    def test_filters_below_threshold(self):
        summaries = [{"score": 8}, {"score": 3}, {"score": 5}]
        out = llm.filter_by_score(summaries, min_score=5)
        assert out == [{"score": 8}, {"score": 5}]

    def test_default_threshold_via_config(self, monkeypatch):
        monkeypatch.setattr("modules.llm.config.MIN_RELEVANCE_SCORE", 6)
        out = llm.filter_by_score([{"score": 6}, {"score": 5}], min_score=None)  # type: ignore[arg-type]
        assert out == [{"score": 6}]


class TestProviderSelection:
    def test_get_provider_respects_order_and_availability(self, monkeypatch):
        p_gem = llm.LLMProvider("gemini", "key")
        p_groq = llm.LLMProvider("groq", "key")
        monkeypatch.setattr(llm, "_providers", {"gemini": p_gem, "groq": p_groq})
        assert llm.get_provider(["groq", "gemini"]).name == "groq"  # type: ignore[union-attr]
        assert llm.get_provider(["gemini", "groq"]).name == "gemini"  # type: ignore[union-attr]

    def test_get_provider_none_when_empty(self, monkeypatch):
        monkeypatch.setattr(llm, "_providers", {})
        assert llm.get_provider() is None

    def test_get_provider_skips_unavailable(self, monkeypatch):
        p = llm.LLMProvider("gemini", "")  # no key -> unavailable
        monkeypatch.setattr(llm, "_providers", {"gemini": p})
        assert llm.get_provider() is None


class TestSummariseBatchFlex:
    @pytest.mark.asyncio
    async def test_maps_indexes_to_articles(self, monkeypatch):
        fake_json = (
            '[{"index":1,"summary":"Great summary","score":9},'
            '{"index":2,"summary":"Okay","score":4}]'
        )
        monkeypatch.setattr(llm, "call_with_fallback", AsyncMock(return_value=fake_json))
        arts = [make_article("A"), make_article("B")]
        out = await llm.summarise_batch_flex(arts)
        assert len(out) == 2
        assert out[0]["article"].title == "A"
        assert out[0]["summary"] == "Great summary"
        assert out[1]["score"] == 4

    @pytest.mark.asyncio
    async def test_empty_articles_short_circuits(self):
        out = await llm.summarise_batch_flex([])
        assert out == []

    @pytest.mark.asyncio
    async def test_unparsable_response_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            llm, "call_with_fallback", AsyncMock(return_value="not json at all")
        )
        out = await llm.summarise_batch_flex([make_article("A")])
        assert out == []
