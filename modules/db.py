"""SQLite state management for production-grade persistence."""

import sqlite3
from datetime import UTC, datetime


class StateDB:
    """Lightweight SQLite database for all state persistence."""

    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize all tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Seen URLs for deduplication
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_urls (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    source TEXT,
                    seen_at TEXT NOT NULL
                )
            """)

            # Daily LLM call tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_calls (
                    date TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0
                )
            """)

            # Source state (last fetch timestamps)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_state (
                    source TEXT PRIMARY KEY,
                    last_fetch TEXT,
                    cursor TEXT
                )
            """)

            # Error logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    module TEXT,
                    error TEXT,
                    context TEXT
                )
            """)

            # Delivery log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delivery_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    article_url TEXT,
                    article_title TEXT,
                    telegram_chat_id TEXT,
                    status TEXT
                )
            """)

            # YouTube videos (delta check + stats refresh)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_videos (
                    video_id          TEXT PRIMARY KEY,
                    channel_id        TEXT,
                    title             TEXT,
                    description       TEXT,
                    thumbnail         TEXT,
                    published_at      TEXT,
                    duration_seconds  INTEGER,
                    tags              TEXT,
                    views             INTEGER DEFAULT 0,
                    likes             INTEGER DEFAULT 0,
                    comment_count     INTEGER DEFAULT 0,
                    transcript        TEXT,
                    scraped_at        TEXT
                )
            """)

            # YouTube comments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS youtube_comments (
                    comment_id   TEXT PRIMARY KEY,
                    video_id     TEXT,
                    author       TEXT,
                    text         TEXT,
                    like_count   INTEGER DEFAULT 0,
                    published_at TEXT,
                    scraped_at   TEXT
                )
            """)

    # --- Seen URLs ---

    def is_seen(self, url_hash: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM seen_urls WHERE url_hash = ?", (url_hash,)
            )
            return cursor.fetchone() is not None

    def mark_seen(self, url_hash: str, url: str, source: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seen_urls (url_hash, url, source, seen_at) VALUES (?, ?, ?, ?)",
                (url_hash, url, source, datetime.now(UTC).isoformat()),
            )

    def get_seen_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM seen_urls")
            return cursor.fetchone()[0]

    def prune_old_urls(self, days: int = 30):
        """Remove URLs older than N days to prevent DB bloat."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"DELETE FROM seen_urls WHERE seen_at < datetime('now', '-{days} days')"
            )

    # --- Daily LLM Calls ---

    def get_daily_call_count(self) -> int:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT count FROM daily_calls WHERE date = ?", (today,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    def increment_daily_calls(self, count: int = 1):
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO daily_calls (date, count) VALUES (?, ?) "
                "ON CONFLICT(date) DO UPDATE SET count = count + ?",
                (today, count, count),
            )

    # --- Source State ---

    def get_last_fetch(self, source: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT last_fetch FROM source_state WHERE source = ?", (source,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def set_last_fetch(self, source: str, timestamp: str, cursor: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO source_state (source, last_fetch, cursor) VALUES (?, ?, ?) "
                "ON CONFLICT(source) DO UPDATE SET last_fetch = ?, cursor = ?",
                (source, timestamp, cursor, timestamp, cursor),
            )

    # --- Error Logging ---

    def log_error(self, module: str, error: str, context: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO error_log (timestamp, module, error, context) VALUES (?, ?, ?, ?)",
                (datetime.now(UTC).isoformat(), module, str(error), context),
            )

    # --- Delivery Log ---

    def log_delivery(
        self, article_url: str, article_title: str, chat_id: str, status: str
    ):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO delivery_log (timestamp, article_url, article_title, telegram_chat_id, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now(UTC).isoformat(),
                    article_url,
                    article_title,
                    chat_id,
                    status,
                ),
            )

    # --- YouTube Videos ---

    def is_youtube_video_seen(self, video_id: str) -> bool:
        """Check if a YouTube video has already been processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM youtube_videos WHERE video_id = ?", (video_id,)
            )
            return cursor.fetchone() is not None

    def upsert_youtube_video(self, video: dict):
        """Insert or update a YouTube video record (always refresh stats)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO youtube_videos
                   (video_id, channel_id, title, description, thumbnail,
                    published_at, duration_seconds, tags,
                    views, likes, comment_count, transcript, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(video_id) DO UPDATE SET
                    views = excluded.views,
                    likes = excluded.likes,
                    comment_count = excluded.comment_count,
                    scraped_at = excluded.scraped_at
                """,
                (
                    video["video_id"],
                    video.get("channel_id", ""),
                    video.get("title", ""),
                    video.get("description", ""),
                    video.get("thumbnail", ""),
                    video.get("published_at", ""),
                    video.get("duration_seconds", 0),
                    video.get("tags", "[]"),
                    video.get("views", 0),
                    video.get("likes", 0),
                    video.get("comment_count", 0),
                    video.get("transcript", ""),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def update_youtube_video_stats(self, video_id: str, views: int, likes: int, comment_count: int):
        """Refresh stats for an already-processed video."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE youtube_videos
                   SET views = ?, likes = ?, comment_count = ?,
                       scraped_at = ?
                   WHERE video_id = ?""",
                (views, likes, comment_count,
                 datetime.now(UTC).isoformat(), video_id),
            )

    def insert_youtube_comments(self, comments: list):
        """Bulk insert comments with deduplication."""
        with sqlite3.connect(self.db_path) as conn:
            for c in comments:
                conn.execute(
                    """INSERT OR IGNORE INTO youtube_comments
                       (comment_id, video_id, author, text,
                        like_count, published_at, scraped_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        c.get("comment_id", ""),
                        c.get("video_id", ""),
                        c.get("author", ""),
                        c.get("text", ""),
                        c.get("like_count", 0),
                        c.get("published_at", ""),
                        datetime.now(UTC).isoformat(),
                    ),
                )


# Singleton instance for global use
db = StateDB()
