"""SQLite state management for production-grade persistence."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Optional

import config


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
                (url_hash, url, source, datetime.now(timezone.utc).isoformat()),
            )

    def get_seen_count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM seen_urls")
            return cursor.fetchone()[0]

    def prune_old_urls(self, days: int = 30):
        """Remove URLs older than N days to prevent DB bloat."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM seen_urls WHERE seen_at < datetime('now', '-{} days')".format(
                    days
                )
            )

    # --- Daily LLM Calls ---

    def get_daily_call_count(self) -> int:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT count FROM daily_calls WHERE date = ?", (today,)
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    def increment_daily_calls(self, count: int = 1):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO daily_calls (date, count) VALUES (?, ?) "
                "ON CONFLICT(date) DO UPDATE SET count = count + ?",
                (today, count, count),
            )

    # --- Source State ---

    def get_last_fetch(self, source: str) -> Optional[str]:
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
                (datetime.now(timezone.utc).isoformat(), module, str(error), context),
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
                    datetime.now(timezone.utc).isoformat(),
                    article_url,
                    article_title,
                    chat_id,
                    status,
                ),
            )


# Singleton instance for global use
db = StateDB()
