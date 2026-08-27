"""Unit tests for modules/fetcher.py and modules/apify_fetcher.py pure logic.

Covers the deterministic, network-free helpers that previously had no test
coverage (flagged in PROGRESS.md under "Broaden unit coverage"):

  modules/fetcher.py
    - strip_html          (HTML -> plain text via lxml/BeautifulSoup)
    - normalise_url       (scheme://netloc/path, drops query/fragment)
    - hash_url            (md5 of the normalised url)
    - extract_rss_text    (summary/description/content selection + 400-char cap)
    - Article             (normalisation + url_hash derivation)

  modules/apify_fetcher.py
    - is_ai_related       (keyword membership check)

No network, no API keys, no aiohttp sessions. External fetchers
(fetch_rss_feed, fetch_hackernews, fetch_arxiv, fetch_twitter, fetch_reddit)
are intentionally excluded — they require live HTTP and are smoke-tested by the
live `test_*` suite instead.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime

from modules import fetcher
from modules.apify_fetcher import is_ai_related


# --------------------------------------------------------------------------- #
# strip_html
# --------------------------------------------------------------------------- #
class TestStripHtml:
    def test_empty_returns_empty(self):
        assert fetcher.strip_html("") == ""

    def test_none_returns_empty(self):
        # None is falsy -> guarded to ""
        assert fetcher.strip_html(None) == ""  # type: ignore[arg-type]

    def test_strips_tags(self):
        assert fetcher.strip_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_strips_and_collapses_whitespace(self):
        assert fetcher.strip_html("   <div>  spaced  </div>   ") == "spaced"

    def test_preserves_internal_text(self):
        assert fetcher.strip_html("<ul><li>one</li><li>two</li></ul>") == "one two"


# --------------------------------------------------------------------------- #
# normalise_url
# --------------------------------------------------------------------------- #
class TestNormaliseUrl:
    def test_empty_returns_empty(self):
        assert fetcher.normalise_url("") == ""

    def test_drops_query_and_fragment(self):
        # query/fragment must not survive normalisation
        out = fetcher.normalise_url("https://blog.example.com/a/b?x=1&y=2#frag")
        assert out == "https://blog.example.com/a/b"

    def test_keeps_scheme_netloc_path(self):
        assert fetcher.normalise_url("http://x.io/p") == "http://x.io/p"

    def test_no_trailing_slash_added(self):
        # normalise_url only echoes scheme://netloc/path — must not invent a slash
        assert fetcher.normalise_url("https://example.com") == "https://example.com"


# --------------------------------------------------------------------------- #
# hash_url
# --------------------------------------------------------------------------- #
class TestHashUrl:
    def test_empty_returns_md5_of_empty_string(self):
        # fetcher.hash_url computes md5(normalise_url(url)); normalise_url("") -> ""
        # so the empty input hashes to the md5 of the empty string (NOT "").
        # This is intentionally distinct from dedup.hash_url, which returns "".
        assert fetcher.hash_url("") == "d41d8cd98f00b204e9800998ecf8427e"

    def test_none_matches_empty(self):
        # None is falsy -> normalised to "" -> identical digest to empty input
        assert fetcher.hash_url(None) == fetcher.hash_url("")  # type: ignore[arg-type]

    def test_deterministic(self):
        a = fetcher.hash_url("https://a.com/x")
        b = fetcher.hash_url("https://a.com/x")
        assert a == b
        assert len(a) == 32  # md5 hex digest

    def test_ignores_query_and_fragment(self):
        # hash is computed over the *normalised* url, so query/fragment collapse
        assert fetcher.hash_url("https://a.com/x?a=1") == fetcher.hash_url(
            "https://a.com/x#frag"
        )

    def test_distinct_urls_distinct_hashes(self):
        assert fetcher.hash_url("https://a.com/x") != fetcher.hash_url("https://a.com/y")


# --------------------------------------------------------------------------- #
# extract_rss_text
# --------------------------------------------------------------------------- #
class _Entry:
    """Minimal stand-in for a feedparser entry with chosen attributes.

    Mirrors feedparser: accessing an unset attribute raises AttributeError
    (so ``hasattr`` works the way ``extract_rss_text`` expects), rather than
    silently returning None.
    """

    def __init__(self, **attrs):
        self._attrs = attrs

    def __getattr__(self, name):
        if name in self._attrs:
            return self._attrs[name]
        raise AttributeError(name)


class TestExtractRssText:
    def test_summary_used_when_present(self):
        entry = _Entry(summary="<p>AI news</p>")
        assert fetcher.extract_rss_text(entry) == "AI news"

    def test_description_fallback(self):
        entry = _Entry(description="<p>desc text</p>")
        assert fetcher.extract_rss_text(entry) == "desc text"

    def test_content_fallback(self):
        entry = _Entry(content=[type("C", (), {"value": "<p>c</p>"})()])
        assert fetcher.extract_rss_text(entry) == "c"

    def test_no_fields_returns_empty(self):
        assert fetcher.extract_rss_text(_Entry()) == ""

    def test_truncates_to_400_chars(self):
        long_text = "x" * 1000
        out = fetcher.extract_rss_text(_Entry(summary=long_text))
        assert len(out) == 400
        assert out == "x" * 400


# --------------------------------------------------------------------------- #
# Article
# --------------------------------------------------------------------------- #
class TestArticle:
    def test_url_is_normalised(self):
        a = fetcher.Article("T", "https://e.com/p?q=1", "b", "src")
        assert a.url == "https://e.com/p"

    def test_url_hash_matches_hash_url(self):
        url = "https://e.com/p?q=1"
        a = fetcher.Article("T", url, "b", "src")
        assert a.url_hash == fetcher.hash_url(url)

    def test_default_score_is_zero(self):
        a = fetcher.Article("T", "https://e.com/p", "b", "src")
        assert a.score == 0

    def test_default_published_is_datetime(self):
        a = fetcher.Article("T", "https://e.com/p", "b", "src")
        assert isinstance(a.published, datetime)

    def test_explicit_published_preserved(self):
        pub = datetime(2026, 1, 2, 3, 4, 5)
        a = fetcher.Article("T", "https://e.com/p", "b", "src", published=pub)
        assert a.published == pub


# --------------------------------------------------------------------------- #
# is_ai_related (apify_fetcher)
# --------------------------------------------------------------------------- #
class TestIsAiRelated:
    def test_empty_false(self):
        assert is_ai_related("") is False

    def test_none_false(self):
        assert is_ai_related(None) is False  # type: ignore[arg-type]

    def test_clear_ai_phrase_true(self):
        assert is_ai_related("New LLM beats GPT on the benchmark") is True

    def test_openai_true(self):
        assert is_ai_related("OpenAI releases a new model") is True

    def test_transformer_true(self):
        assert is_ai_related("A better transformer architecture") is True

    def test_case_insensitive(self):
        assert is_ai_related("ANTHROPIC CLAUDE UPDATE") is True

    def test_irrelevant_false(self):
        assert is_ai_related("Recipe for banana bread") is False

    def test_unrelated_sport_false(self):
        assert is_ai_related("Local football team wins the cup") is False
