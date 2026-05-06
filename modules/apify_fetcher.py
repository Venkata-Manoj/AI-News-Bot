"""Direct scraping for X (Twitter) and Reddit - no Apify actors needed.

Uses free alternatives:
- Twitter: Nitter RSS feeds (free, no API key)
- Reddit: Reddit public JSON API (free, no API key)
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp

import config
from modules.db import db


# Nitter instances with RSS support (tested May 2026)
NITTER_INSTANCES = [
    "nitter.net",  # Netherlands - fast, reliable
    "nitter.privacyredirect.com",  # Finland
    "xcancel.com",  # USA - fork with RSS
    "nitter.kuuro.net",  # USA - RSS support
]

REDDIT_API_BASE = "https://www.reddit.com"

# Target accounts and subreddits
TWITTER_ACCOUNTS = [
    "sama",
    "elonmusk",
    "satyanadella",
    "ylecun",
    "karpathy",
    "jeremyphoward",
    "Gradio",
    "huggingface",
]

REDDIT_SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "OpenAI",
    "LocalLLaMA",
    "singularity",
    "ChatGPT",
]


class DirectFetcher:
    """Direct scraping - no external API needed.
    - Twitter: Nitter RSS (free, no API key)
    - Reddit: Reddit JSON API (free, no API key)
    """

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": "AI-News-Bot/1.0"})
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch_twitter(
        self, accounts: List[str] = None, increment: bool = True
    ) -> List[dict]:
        """Fetch recent tweets via Nitter RSS feeds (free, no API key)."""
        if not accounts:
            accounts = TWITTER_ACCOUNTS

        all_items = []
        errors = []

        for account in accounts:
            try:
                items = await self._fetch_nitter(account)
                all_items.extend(items)
            except Exception as e:
                errors.append(f"{account}: {e}")
                continue

        if errors:
            print(f"[Twitter] Errors: {', '.join(errors[:3])}")

        return all_items

    async def _fetch_nitter(self, username: str) -> List[dict]:
        """Fetch tweets from Nitter RSS feed."""
        import feedparser

        for instance in NITTER_INSTANCES:
            try:
                url = f"https://{instance}/rss.php?username={username}"
                async with self.session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        continue

                    text = await resp.text()
                    feed = feedparser.parse(text)

                    items = []
                    for entry in feed.entries[:10]:
                        # Extract tweet text (remove BBC title prefix)
                        title = entry.get("title", "")
                        if title.startswith(f"@{username}: "):
                            title = title[len(f"@{username}: ") :]

                        items.append(
                            {
                                "text": title,
                                "url": entry.get("link", ""),
                                "timestamp": entry.get("published", ""),
                                "username": username,
                            }
                        )

                    if items:
                        print(
                            f"[Twitter] {username}: {len(items)} tweets via {instance}"
                        )
                        return items

            except Exception:
                continue

        raise Exception(f"All {len(NITTER_INSTANCES)} Nitter instances failed")

    async def fetch_reddit(
        self, subreddits: List[str] = None, increment: bool = True
    ) -> List[dict]:
        """Fetch recent posts from Reddit's public JSON API (free, no API key)."""
        if not subreddits:
            subreddits = REDDIT_SUBREDDITS

        all_posts = []

        for subreddit in subreddits[:5]:  # Limit to avoid rate limits
            try:
                posts = await self._fetch_subreddit(subreddit)
                all_posts.extend(posts)
                await asyncio.sleep(1.5)  # Rate limit
            except Exception as e:
                print(f"[Reddit] r/{subreddit} error: {e}")
                continue

        return all_posts

    async def _fetch_subreddit(self, subreddit: str, limit: int = 20) -> List[dict]:
        """Fetch posts from a single subreddit."""
        url = f"{REDDIT_API_BASE}/r/{subreddit}/hot.json"
        params = {"limit": min(limit, 25), "raw_json": 1}

        async with self.session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")

            data = await resp.json()
            children = data.get("data", {}).get("children", [])

            posts = []
            for child in children:
                post = child.get("data", {})
                posts.append(
                    {
                        "title": post.get("title", ""),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "body": post.get("selftext", ""),
                        "subreddit": post.get("subreddit", ""),
                        "score": post.get("score", 0),
                        "created": post.get("created_utc", ""),
                        "author": post.get("author", ""),
                    }
                )

            print(f"[Reddit] r/{subreddit}: {len(posts)} posts")
            return posts


# Keep ApifyFetcher for backward compatibility (now just wraps DirectFetcher)
class ApifyFetcher:
    """Legacy class - now uses direct scraping instead of Apify actors."""

    def __init__(self, api_token: str = None):
        self.api_token = api_token
        self._direct = DirectFetcher()

    async def __aenter__(self):
        await self._direct.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self._direct.__aexit__(*args)

    async def fetch_twitter(
        self, accounts: List[str] = None, increment: bool = True
    ) -> List[dict]:
        return await self._direct.fetch_twitter(accounts, increment)

    async def fetch_reddit(
        self, subreddits: List[str] = None, increment: bool = True
    ) -> List[dict]:
        return await self._direct.fetch_reddit(subreddits, increment)

    # --- Content Filtering ---

    def _is_ai_related(self, text: str) -> bool:
        """Quick check if content is AI-related."""
        ai_keywords = [
            "ai",
            "artificial intelligence",
            "machine learning",
            "ml",
            "deep learning",
            "neural",
            "gpt",
            "llm",
            "language model",
            "transformer",
            "openai",
            "anthropic",
            "claude",
            "chatgpt",
            "sora",
            "gemini",
            "mistral",
            "llama",
            "stable diffusion",
            "huggingface",
            "benchmark",
            "sota",
            "arxiv",
            "research",
            "model",
            "training",
            "inference",
            "agent",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in ai_keywords)


# Convenience functions for easy import
async def fetch_twitter_posts(accounts: List[str] = None) -> List[dict]:
    """Fetch tweets via Nitter RSS (free, no API key needed)."""
    async with DirectFetcher() as fetcher:
        return await fetcher.fetch_twitter(accounts)


async def fetch_reddit_posts(subreddits: List[str] = None) -> List[dict]:
    """Fetch Reddit posts via direct JSON API (free, no API key needed)."""
    async with DirectFetcher() as fetcher:
        return await fetcher.fetch_reddit(subreddits)


def is_ai_related(text: str) -> bool:
    """Quick check if content is AI-related."""
    ai_keywords = [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
        "deep learning",
        "neural",
        "gpt",
        "llm",
        "language model",
        "transformer",
        "openai",
        "anthropic",
        "claude",
        "chatgpt",
        "sora",
        "gemini",
        "mistral",
        "llama",
        "stable diffusion",
        "huggingface",
        "benchmark",
        "sota",
        "arxiv",
        "research",
        "model",
        "training",
        "inference",
        "agent",
        "claude",
        "gemma",
        "flux",
        "sdxl",
    ]
    return any((kw in text.lower()) for kw in ai_keywords)
