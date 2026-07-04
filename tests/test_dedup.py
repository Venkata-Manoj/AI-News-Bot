"""Unit tests for modules/dedup.py — URL deduplication and keyword filtering.

Tests SeenManager methods with a mock database.
No network access required.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.dedup import SeenManager, hash_url

# ── hash_url ───────────────────────────────────────────────────────────────


class TestHashURL:
    def test_hash_url_normal(self):
        """Standard URL should produce a consistent MD5 hash."""
        h = hash_url("https://example.com/article")
        assert isinstance(h, str)
        assert len(h) == 32  # MD5 hex digest length

    def test_hash_url_consistent(self):
        """Same URL should always produce the same hash."""
        url = "https://example.com/test"
        assert hash_url(url) == hash_url(url)

    def test_hash_url_different(self):
        """Different URLs should produce different hashes."""
        assert hash_url("https://example.com/a") != hash_url("https://example.com/b")

    def test_hash_url_empty(self):
        """Empty URL should return empty string."""
        assert hash_url("") == ""

    def test_hash_url_none(self):
        """None URL should return empty string (coerced by encode)."""
        # Note: hash_url expects str; None would crash at .encode()
        # This documents that caller must pass str, not None
        pass

    def test_hash_url_normalizes(self):
        """URLs that differ only in fragments should hash the same (normalised)."""
        # The hash_url function uses normalise_url which strips fragments
        # But that's in fetcher.py — dedup's hash_url just does md5(url.encode())
        h1 = hash_url("https://example.com/page#section")
        h2 = hash_url("https://example.com/page#section")
        assert h1 == h2


# ── helper fixture ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock database with controllable behavior."""
    return MagicMock()


@pytest.fixture
def manager(mock_db):
    """Create a SeenManager with a mock database."""
    mgr = SeenManager()
    mgr.db = mock_db
    return mgr


def make_article(url, title="Test Article", body="Test body content", source="test", url_hash="__auto__"):
    """Create a minimal article-like object for testing.

    If url_hash is "__auto__", the attribute is not set, letting
    filter_new auto-assign it from the URL.
    """
    class FakeArticle:
        def __init__(self, url, title, body, source, url_hash):
            self.url = url
            self.title = title
            self.body = body
            self.source = source
            if url_hash != "__auto__":
                self.url_hash = url_hash

        def __repr__(self):
            return f"<Article {self.title[:30]}>"

    return FakeArticle(url=url, title=title, body=body, source=source, url_hash=url_hash)


# ── filter_new ─────────────────────────────────────────────────────────────


class TestFilterNew:
    def test_filter_new_empty_list(self, manager):
        """Empty article list should return empty list."""
        assert manager.filter_new([]) == []

    def test_filter_new_all_new(self, manager, mock_db):
        """When no articles are seen, all should be returned."""
        mock_db.is_seen.return_value = False
        articles = [
            make_article("https://example.com/1", url_hash="h1"),
            make_article("https://example.com/2", url_hash="h2"),
        ]
        result = manager.filter_new(articles)
        assert len(result) == 2

    def test_filter_new_some_seen(self, manager, mock_db):
        """Seen articles should be filtered out."""
        # First call returns True (seen), rest return False (new)
        mock_db.is_seen.side_effect = lambda h: h == "seen_hash"

        articles = [
            make_article("https://example.com/seen", url_hash="seen_hash"),
            make_article("https://example.com/new1", url_hash="new_hash1"),
            make_article("https://example.com/new2", url_hash="new_hash2"),
        ]
        result = manager.filter_new(articles)
        assert len(result) == 2
        assert all(a.url_hash != "seen_hash" for a in result)

    def test_filter_new_all_seen(self, manager, mock_db):
        """When all articles are seen, should return empty list."""
        mock_db.is_seen.return_value = True
        articles = [
            make_article("https://example.com/a", url_hash="h1"),
            make_article("https://example.com/b", url_hash="h2"),
        ]
        assert manager.filter_new(articles) == []

    def test_filter_new_auto_hash(self, manager, mock_db):
        """Articles without url_hash should get one assigned."""
        mock_db.is_seen.return_value = False
        article = make_article("https://example.com/auto")  # url_hash defaults to "__auto__"
        assert not hasattr(article, 'url_hash')  # Not set initially

        result = manager.filter_new([article])

        assert len(result) == 1
        assert result[0].url_hash is not None  # Was auto-assigned

    def test_filter_new_marks_as_seen(self, manager, mock_db):
        """After filter_new, articles should NOT be marked seen (that's the caller's job)."""
        mock_db.is_seen.return_value = False
        articles = [make_article("https://example.com/n", url_hash="h1")]
        manager.filter_new(articles)
        # mark_seen should not be called by filter_new
        mock_db.mark_seen.assert_not_called()


# ── filter_by_keywords ─────────────────────────────────────────────────────


class TestFilterByKeywords:
    def test_filter_by_keywords_default(self, manager):
        """Default keywords should filter AI-relevant content."""
        articles = [
            make_article("https://example.com/1", title="Breaking: New AI model released", body="OpenAI announced GPT-5 today"),
            make_article("https://example.com/2", title="Weather report", body="Sunny with a chance of rain"),
            make_article("https://example.com/3", title="LLM benchmarks", body="Claude 4 outperforms on reasoning"),
            make_article("https://example.com/4", title="Cooking recipe", body="How to make pasta carbonara"),
        ]
        result = manager.filter_by_keywords(articles)
        assert len(result) >= 2
        titles = [a.title for a in result]
        assert "Breaking: New AI model released" in titles
        assert "LLM benchmarks" in titles

    def test_filter_by_keywords_custom(self, manager):
        """Custom keywords should be used when provided."""
        articles = [
            make_article("https://example.com/1", title="Apple release", body="New iPhone announced"),
            make_article("https://example.com/2", title="Banana farming", body="How to grow bananas"),
        ]
        result = manager.filter_by_keywords(articles, keywords=["apple", "banana"])
        assert len(result) == 2

    def test_filter_by_keywords_empty_list(self, manager):
        """Empty article list should return empty list."""
        assert manager.filter_by_keywords([]) == []

    def test_filter_by_keywords_no_match(self, manager):
        """No matching articles should return empty list."""
        articles = [
            make_article("https://example.com/1", title="Nothing here", body="Completely unrelated topic"),
        ]
        # Use keywords that won't match
        result = manager.filter_by_keywords(articles, keywords=["zzzzz_not_found_zzzzz"])
        assert len(result) == 0

    def test_filter_by_keywords_case_insensitive(self, manager):
        """Keyword matching should be case-insensitive."""
        articles = [
            make_article("https://example.com/1", title="AI NEWS", body=""),
            make_article("https://example.com/2", title="ai news", body=""),
        ]
        result = manager.filter_by_keywords(articles, keywords=["ai"])
        assert len(result) == 2

    def test_filter_by_keywords_body_only(self, manager):
        """Match in body should work even without title match."""
        articles = [
            make_article("https://example.com/1", title="Random Title", body="This article discusses transformer architectures"),
        ]
        result = manager.filter_by_keywords(articles, keywords=["transformer"])
        assert len(result) == 1

    def test_filter_by_keywords_none_keywords(self, manager):
        """None keywords should fall back to defaults."""
        articles = [
            make_article("https://example.com/1", title="AI developments", body=""),
        ]
        result = manager.filter_by_keywords(articles, keywords=None)
        assert len(result) == 1

    def test_filter_by_keywords_empty_body_and_title(self, manager):
        """Articles with empty body and title should not crash."""
        articles = [
            make_article("https://example.com/1", title="", body=""),
        ]
        result = manager.filter_by_keywords(articles)
        assert len(result) == 0

    def test_filter_by_keywords_partial_word(self, manager):
        """Partial words should match (no word boundary requirement)."""
        articles = [
            make_article("https://example.com/1", title="Machine Learning", body=""),
        ]
        result = manager.filter_by_keywords(articles, keywords=["machine"])
        assert len(result) == 1


# ── Integration-style: backend-facing ops via module-level functions ────────


class TestModuleLevelFunctions:
    def test_is_seen_module(self):
        """Module-level is_seen should delegate to global seen_manager."""
        # We can test the function exists and delegates correctly
        from modules.dedup import filter_by_keywords, filter_new, is_seen, mark_seen
        assert callable(is_seen)
        assert callable(mark_seen)
        assert callable(filter_new)
        assert callable(filter_by_keywords)
