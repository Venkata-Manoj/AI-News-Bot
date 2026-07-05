"""Unit tests for modules/db.py — SQLite state management.

Tests all CRUD operations and edge cases using in-memory SQLite.
No network access required.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.db import StateDB


@pytest.fixture
def db():
    """Create a fresh temporary StateDB for each test.

    Uses a temporary file instead of :memory: because SQLite creates a new
    in-memory database for every connection, so _init_db() tables created in
    __init__ would not exist in subsequent method calls.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
    db_obj = StateDB(db_path=tmp_path)
    yield db_obj
    os.unlink(tmp_path)


# ── Seen URLs ─────────────────────────────────────────────────────────────


class TestSeenURLs:
    def test_is_seen_empty(self, db):
        """A URL not yet seen should return False."""
        assert db.is_seen("nonexistent_hash") is False

    def test_mark_and_is_seen(self, db):
        """After marking, is_seen should return True."""
        db.mark_seen("abc123", "https://example.com/article", "rss")
        assert db.is_seen("abc123") is True

    def test_mark_seen_default_source(self, db):
        """mark_seen with empty source should still work."""
        db.mark_seen("hash1", "https://example.com/1")
        assert db.is_seen("hash1") is True

    def test_is_seen_wrong_hash(self, db):
        """Different hash should not be seen."""
        db.mark_seen("hash_a", "https://example.com/a", "rss")
        assert db.is_seen("hash_b") is False

    def test_mark_seen_duplicate(self, db):
        """Marking the same URL hash twice should not error (INSERT OR IGNORE)."""
        db.mark_seen("dup_hash", "https://example.com/dup", "rss")
        db.mark_seen("dup_hash", "https://example.com/dup", "rss")  # second insert
        assert db.is_seen("dup_hash") is True
        assert db.get_seen_count() == 1

    def test_get_seen_count(self, db):
        """Should return the correct count of seen URLs."""
        assert db.get_seen_count() == 0
        db.mark_seen("h1", "https://example.com/1", "rss")
        db.mark_seen("h2", "https://example.com/2", "hn")
        assert db.get_seen_count() == 2

    def test_prune_old_urls(self, db):
        """prune_old_urls should remove entries older than N days."""
        # Manually insert an old URL (bypass normal mark_seen which uses current time)
        import sqlite3

        with sqlite3.connect(":memory:") as conn:
            # Can't share connection with db instance since it's :memory:
            pass

        # For :memory: DB, prune_old_urls requires shared access.
        # Use a tempfile-based approach for this test.
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name

        try:
            db_file = StateDB(db_path=tmp_path)
            db_file.mark_seen("old_hash", "https://example.com/old", "test")

            # Manually backdate the entry
            import sqlite3

            with sqlite3.connect(tmp_path) as conn:
                conn.execute(
                    "UPDATE seen_urls SET seen_at = '2020-01-01T00:00:00+00:00' WHERE url_hash = ?",
                    ("old_hash",),
                )

            db_file.mark_seen("new_hash", "https://example.com/new", "test")

            assert db_file.get_seen_count() == 2

            # Prune URLs older than 7 days — only old_hash should go
            db_file.prune_old_urls(days=7)
            assert db_file.get_seen_count() == 1
            assert db_file.is_seen("new_hash") is True
            assert db_file.is_seen("old_hash") is False
        finally:
            os.unlink(tmp_path)

    def test_prune_old_urls_none(self, db):
        """prune_old_urls on empty DB should not error."""
        db.prune_old_urls(days=30)  # should not raise


# ── Daily LLM Calls ───────────────────────────────────────────────────────


class TestDailyCalls:
    def test_get_daily_call_count_initial(self, db):
        """Initial daily call count should be 0."""
        assert db.get_daily_call_count() == 0

    def test_increment_and_get(self, db):
        """Incrementing should reflect in get count."""
        db.increment_daily_calls(5)
        assert db.get_daily_call_count() == 5

    def test_increment_multiple(self, db):
        """Multiple increments should sum."""
        db.increment_daily_calls(3)
        db.increment_daily_calls(7)
        assert db.get_daily_call_count() == 10

    def test_increment_default(self, db):
        """Default increment is 1."""
        db.increment_daily_calls()
        assert db.get_daily_call_count() == 1


# ── Source State ───────────────────────────────────────────────────────────


class TestSourceState:
    def test_get_last_fetch_empty(self, db):
        """Unknown source should return None."""
        assert db.get_last_fetch("nonexistent") is None

    def test_set_and_get(self, db):
        """Setting last fetch should return it."""
        db.set_last_fetch("rss", "2026-07-04T12:00:00")
        assert db.get_last_fetch("rss") == "2026-07-04T12:00:00"

    def test_update_last_fetch(self, db):
        """Updating a source should overwrite the previous value."""
        db.set_last_fetch("hn", "2026-07-03T00:00:00")
        db.set_last_fetch("hn", "2026-07-04T00:00:00", cursor="page2")
        assert db.get_last_fetch("hn") == "2026-07-04T00:00:00"

    def test_multiple_sources(self, db):
        """Different sources should have independent state."""
        db.set_last_fetch("rss", "A")
        db.set_last_fetch("hn", "B")
        assert db.get_last_fetch("rss") == "A"
        assert db.get_last_fetch("hn") == "B"


# ── Error Logging ──────────────────────────────────────────────────────────


class TestErrorLog:
    def test_log_error(self, db):
        """Logging an error should not raise."""
        db.log_error("test_module", "something broke", "context info")
        # Just verify no exception — we can't easily query error_log without
        # exposing a method, but the table should exist and accept inserts.

    def test_log_error_minimal(self, db):
        """Error log with minimal params should work."""
        db.log_error("module", "error")

    def test_log_error_empty_context(self, db):
        """Empty context string should not cause issues."""
        db.log_error("module", "error", "")


# ── Delivery Log ───────────────────────────────────────────────────────────


class TestDeliveryLog:
    def test_log_delivery(self, db):
        """Logging a delivery should not raise."""
        db.log_delivery("https://example.com/a", "Test Article", "chat123", "sent")

    def test_log_delivery_failed_status(self, db):
        """'failed' status should be accepted."""
        db.log_delivery("https://example.com/b", "Failed Article", "chat123", "failed")

    def test_log_delivery_empty_fields(self, db):
        """Empty fields should not cause SQL errors."""
        db.log_delivery("", "", "", "")


# ── YouTube Videos ─────────────────────────────────────────────────────────


class TestYouTubeVideos:
    def test_is_youtube_video_seen_empty(self, db):
        """Unknown video ID should return False."""
        assert db.is_youtube_video_seen("nonexistent") is False

    def test_upsert_and_check(self, db):
        """After upsert, is_youtube_video_seen should return True."""
        video = {
            "video_id": "abc123",
            "channel_id": "UC_test",
            "title": "Test Video",
            "description": "A test video",
            "thumbnail": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
            "published_at": "2026-01-01T00:00:00Z",
            "duration_seconds": 300,
            "tags": '["test", "demo"]',
            "views": 1000,
            "likes": 50,
            "comment_count": 10,
            "transcript": "Hello world",
        }
        db.upsert_youtube_video(video)
        assert db.is_youtube_video_seen("abc123") is True

    def test_upsert_minimal(self, db):
        """Upsert with minimal fields should work."""
        video = {"video_id": "min123"}
        db.upsert_youtube_video(video)
        assert db.is_youtube_video_seen("min123") is True

    def test_update_stats(self, db):
        """update_youtube_video_stats should not raise."""
        video = {"video_id": "stats123"}
        db.upsert_youtube_video(video)
        db.update_youtube_video_stats("stats123", views=5000, likes=200, comment_count=30)
        # Just verify no exception

    def test_update_stats_nonexistent(self, db):
        """Updating stats for a non-existent video should not raise (UPDATE no-ops)."""
        db.update_youtube_video_stats("nonexistent", 0, 0, 0)

    def test_insert_youtube_comments_empty(self, db):
        """Empty comments list should not raise."""
        db.insert_youtube_comments([])

    def test_insert_youtube_comments(self, db):
        """Comments should insert without error."""
        comments = [
            {
                "comment_id": "c1",
                "video_id": "v1",
                "author": "user1",
                "text": "Great video!",
                "like_count": 5,
                "published_at": "2026-01-01T00:00:00Z",
            },
            {
                "comment_id": "c2",
                "video_id": "v1",
                "author": "user2",
                "text": "Nice!",
                "like_count": 2,
                "published_at": "2026-01-02T00:00:00Z",
            },
        ]
        db.insert_youtube_comments(comments)

    def test_insert_youtube_comments_minimal(self, db):
        """Comments with only required fields should work."""
        comments = [{"comment_id": "c_min", "video_id": "v1"}]
        db.insert_youtube_comments(comments)

    def test_insert_youtube_comments_dedup(self, db):
        """Duplicate comment IDs should be ignored (INSERT OR IGNORE)."""
        comments = [
            {"comment_id": "c_dup", "video_id": "v1", "author": "user1", "text": "First"},
            {"comment_id": "c_dup", "video_id": "v1", "author": "user1", "text": "Duplicate"},
        ]
        db.insert_youtube_comments(comments)
        # Should not raise
