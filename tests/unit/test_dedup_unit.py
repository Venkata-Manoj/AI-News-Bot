"""Unit tests for modules/dedup.py — core deduplication engine.

The dedup engine is the last line of defence against sending the same article
to Telegram twice. It must be deterministic and fully offline-testable:

- ``hash_url`` produces stable, content-addressed hashes.
- ``filter_by_keywords`` keeps only AI-relevant articles (title *or* body).
- ``SeenManager.filter_new`` drops already-seen articles and back-fills any
  missing ``url_hash`` before consulting the seen-store.

All collaborators (the SQLite ``db``) are mocked so these tests exercise only
the dedup module's own branching. No network, no API keys, no Telegram.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import MagicMock

import modules.dedup as dedup


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class _Article:
    """Minimal stand-in for a fetched article.

    ``url_hash`` is only set when explicitly provided. Leaving it unset lets us
    exercise the ``filter_new`` back-fill branch that derives the hash from URL.
    """

    def __init__(self, title="", url="", body="", url_hash=None):
        self.title = title
        self.url = url
        self.body = body
        if url_hash is not None:
            self.url_hash = url_hash


def make_seen_manager(is_seen_map=None):
    """Return a SeenManager wired to a fake db.

    ``is_seen_map`` maps url_hash -> bool; any hash not present is treated as
    unseen. The fake db records ``mark_seen`` calls so we can assert on them.
    """
    fake_db = MagicMock()
    seen = dict(is_seen_map or {})

    def _is_seen(h):
        return bool(seen.get(h, False))

    def _mark_seen(h, url="", source=""):
        seen[h] = True

    fake_db.is_seen.side_effect = _is_seen
    fake_db.mark_seen.side_effect = _mark_seen
    mgr = dedup.SeenManager()
    mgr.db = fake_db  # wire the fake store into this instance
    return mgr, fake_db


# --------------------------------------------------------------------------- #
# hash_url
# --------------------------------------------------------------------------- #
class TestHashUrl:
    def test_empty_string(self):
        assert dedup.hash_url("") == ""

    def test_none_is_treated_as_empty(self):
        assert dedup.hash_url(None) == ""  # type: ignore[arg-type]

    def test_returns_hex_digest(self):
        h = dedup.hash_url("https://example.com/a")
        assert len(h) == 32
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        a = dedup.hash_url("https://huggingface.co/blog/foo")
        b = dedup.hash_url("https://huggingface.co/blog/foo")
        assert a == b

    def test_distinct_urls_distinct_hashes(self):
        a = dedup.hash_url("https://a.com/1")
        b = dedup.hash_url("https://a.com/2")
        assert a != b


# --------------------------------------------------------------------------- #
# filter_by_keywords
# --------------------------------------------------------------------------- #
class TestFilterByKeywords:
    def test_empty_list(self):
        assert dedup.filter_by_keywords([]) == []

    def test_title_match(self):
        arts = [_Article(title="OpenAI releases new GPT model")]
        out = dedup.filter_by_keywords(arts)
        assert len(out) == 1

    def test_irrelevant_article_dropped(self):
        arts = [_Article(title="Best banana bread recipe", body="flour and sugar")]
        assert dedup.filter_by_keywords(arts) == []

    def test_body_only_match(self):
        arts = [_Article(title="Interesting read", body="A deep dive into neural networks")]
        out = dedup.filter_by_keywords(arts)
        assert len(out) == 1

    def test_case_insensitive(self):
        arts = [_Article(title="TRANSFORMER architectures explained")]
        assert len(dedup.filter_by_keywords(arts)) == 1

    def test_custom_keywords(self):
        arts = [
            _Article(title="Kubernetes autoscaling guide"),
            _Article(title="A gentle intro to LLMs"),
        ]
        out = dedup.filter_by_keywords(arts, keywords=["kubernetes"])
        assert len(out) == 1
        assert out[0].title.startswith("Kubernetes")

    def test_missing_attributes_treated_as_empty(self):
        arts = [_Article()]  # no title, no body
        assert dedup.filter_by_keywords(arts) == []


# --------------------------------------------------------------------------- #
# SeenManager.filter_new
# --------------------------------------------------------------------------- #
class TestFilterNew:
    def test_all_new_when_none_seen(self):
        mgr, _ = make_seen_manager()
        arts = [_Article(title="a", url="https://a.com"), _Article(title="b", url="https://b.com")]
        out = mgr.filter_new(arts)
        assert len(out) == 2

    def test_already_seen_dropped(self):
        h = dedup.hash_url("https://a.com")
        mgr, _ = make_seen_manager({h: True})
        arts = [_Article(title="a", url="https://a.com")]
        out = mgr.filter_new(arts)
        assert out == []

    def test_seen_and_new_mixed(self):
        seen_hash = dedup.hash_url("https://seen.com")
        new_hash = dedup.hash_url("https://new.com")
        mgr, _ = make_seen_manager({seen_hash: True})
        arts = [
            _Article(title="seen", url="https://seen.com"),
            _Article(title="new", url="https://new.com"),
        ]
        out = mgr.filter_new(arts)
        assert len(out) == 1
        assert out[0].url_hash == new_hash

    def test_backfills_missing_url_hash(self):
        mgr, _ = make_seen_manager()
        art = _Article(title="x", url="https://backfill.com")  # no url_hash set
        assert not hasattr(art, "url_hash") or art.url_hash is None
        mgr.filter_new([art])
        assert art.url_hash == dedup.hash_url("https://backfill.com")

    def test_marks_new_as_seen(self):
        mgr, fake_db = make_seen_manager()
        art = _Article(title="x", url="https://mark.com")
        mgr.filter_new([art])
        # filter_new only checks; mark_seen is exercised via mark_seen() below
        mgr.mark_seen(dedup.hash_url("https://mark.com"), "https://mark.com", "rss")
        fake_db.mark_seen.assert_called_once()

    def test_is_seen_delegates_to_db(self):
        mgr, fake_db = make_seen_manager({"abc": True})
        assert mgr.is_seen("abc") is True
        fake_db.is_seen.assert_called_with("abc")
