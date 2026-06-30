"""Deduplication engine using SQLite for persistence.

Replaces JSON-based storage with production-grade SQLite
to prevent state loss on crashes and enable concurrent access.
"""
import hashlib
import re

from modules.db import db


def hash_url(url: str) -> str:
    """Generate a stable hash for a URL."""
    if not url:
        return ""
    return hashlib.md5(url.encode()).hexdigest()


class SeenManager:
    """Production-grade deduplication using SQLite.

    Replaces JSON files to prevent corruption and enable
    safe concurrent access from multiple processes.
    """

    def __init__(self):
        self.db = db

    def is_seen(self, url_hash: str) -> bool:
        """Check if a URL has been processed."""
        return self.db.is_seen(url_hash)

    def mark_seen(self, url_hash: str, url: str = "", source: str = ""):
        """Mark a URL as processed."""
        self.db.mark_seen(url_hash, url, source)

    def filter_new(self, articles: list) -> list:
        """Return only articles not yet processed."""
        new_articles = []
        for article in articles:
            # Ensure url_hash exists
            if not hasattr(article, 'url_hash'):
                article.url_hash = hash_url(article.url)

            if not self.is_seen(article.url_hash):
                new_articles.append(article)
            else:
                print(f"[Dedup] Skipping duplicate: {getattr(article, 'title', '')[:50]}...")

        print(f"[Dedup] {len(new_articles)} new of {len(articles)} total")
        return new_articles

    def filter_by_keywords(self, articles: list, keywords: list[str] = None) -> list:
        """Filter articles by AI-relevant keywords."""
        if keywords is None:
            keywords = [
                "ai", "artificial intelligence", "machine learning", "ml",
                "deep learning", "neural", "gpt", "llm", "language model",
                "transformer", "openai", "anthropic", "claude", "chatgpt",
                "sora", "gemini", "mistral", "llama", "stable diffusion",
                "huggingface", "benchmark", "sota", "agent", "rag",
            ]

        filtered = []
        pattern = re.compile("|".join(keywords), re.IGNORECASE)

        for article in articles:
            text = f"{getattr(article, 'title', '')} {getattr(article, 'body', '')}"
            if pattern.search(text):
                filtered.append(article)

        print(f"[Dedup] {len(filtered)}/{len(articles)} passed keyword filter")
        return filtered


# Global instance for backward compatibility
seen_manager = SeenManager()


def is_seen(url_hash: str) -> bool:
    """Check if a URL hash has been seen."""
    return seen_manager.is_seen(url_hash)


def mark_seen(url_hash: str):
    """Mark a URL hash as seen."""
    seen_manager.mark_seen(url_hash)


def filter_new(articles: list) -> list:
    """Filter out already-seen articles."""
    return seen_manager.filter_new(articles)


def filter_by_keywords(articles: list, keywords: list[str] = None) -> list:
    """Filter articles by keywords."""
    return seen_manager.filter_by_keywords(articles, keywords)
