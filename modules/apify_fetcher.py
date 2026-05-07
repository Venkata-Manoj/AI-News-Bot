"""Social media fetcher for Twitter + Reddit.

Uses free APIs (no API keys needed):
- Twitter: Nitter RSS feeds (unreliable - many instances blocked)
- Reddit: Reddit public JSON API (reliable)
"""

import asyncio
from datetime import datetime
from typing import List

import aiohttp

import config

# Nitter instances - Twitter RSS is unreliable (many blocking RSS readers)
# Last tested: May 2026
NITTER_INSTANCES = [
    "nitter.net",
    "nitter.privacyredirect.com",
    "xcancel.com",
    "nitter.kuuro.net",
]

REDDIT_API_BASE = "https://www.reddit.com"

# Default targets
TWITTER_ACCOUNTS = ["sama", "elonmusk", "satyanadella", "ylecun", "karpathy"]
REDDIT_SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "OpenAI",
    "LocalLLaMA",
    "singularity",
]


async def fetch_twitter(accounts: List[str] = None, limit: int = 5) -> List[dict]:
    """Fetch tweets via Nitter RSS feeds.

    Note: Twitter RSS is unreliable - most instances block RSS readers.
    """
    if not accounts:
        accounts = TWITTER_ACCOUNTS

    import feedparser

    results = []

    for username in accounts[:5]:
        for instance in NITTER_INSTANCES:
            try:
                url = f"https://{instance}/rss.php?username={username}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=8)
                    ) as resp:
                        if resp.status != 200:
                            continue

                        text = await resp.text()
                        feed = feedparser.parse(text)

                        items = []
                        for entry in feed.entries[:limit]:
                            title = entry.get("title", "")
                            # Skip blocked messages
                            if (
                                "whitelisted" in title.lower()
                                or "not allowed" in title.lower()
                            ):
                                continue
                            if title.startswith(f"@{username}: "):
                                title = title[len(f"@{username}: ") :]

                            if is_ai_related(title):
                                items.append(
                                    {
                                        "text": title,
                                        "url": entry.get("link", ""),
                                        "source": "twitter",
                                        "username": username,
                                        "published": entry.get("published", ""),
                                    }
                                )

                        if items:
                            print(
                                f"[Twitter] {username}: {len(items)} tweets via {instance}"
                            )
                            results.extend(items)
                            break

            except Exception:
                continue

    if not results:
        print("[Twitter] Warning: No tweets fetched (RSS blocked by all instances)")

    return results


async def fetch_reddit(subreddits: List[str] = None, limit: int = 10) -> List[dict]:
    """Fetch Reddit posts via public JSON API (reliable, free)."""
    if not subreddits:
        subreddits = REDDIT_SUBREDDITS

    results = []

    async with aiohttp.ClientSession(
        headers={"User-Agent": "AI-News-Bot/1.0"}
    ) as session:
        for subreddit in subreddits[:5]:
            try:
                url = f"{REDDIT_API_BASE}/r/{subreddit}/hot.json"
                params = {"limit": min(limit, 25), "raw_json": 1}

                async with session.get(
                    url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        continue

                    data = await resp.json()
                    children = data.get("data", {}).get("children", [])

                    for child in children:
                        post = child.get("data", {})
                        text = post.get("title", "") + " " + post.get("selftext", "")

                        if is_ai_related(text):
                            results.append(
                                {
                                    "title": post.get("title", ""),
                                    "url": f"https://reddit.com{post.get('permalink', '')}",
                                    "body": post.get("selftext", ""),
                                    "source": f"r/{post.get('subreddit', '')}",
                                    "score": post.get("score", 0),
                                    "created": post.get("created_utc", 0),
                                }
                            )

                await asyncio.sleep(1.5)  # Rate limit

            except Exception as e:
                print(f"[Reddit] r/{subreddit} error: {e}")
                continue

    print(f"[Reddit] Fetched {len(results)} AI-related posts")
    return results


def is_ai_related(text: str) -> bool:
    """Check if content is AI-related."""
    if not text:
        return False
    text_lower = text.lower()
    keywords = [
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
        "huggingface",
        "benchmark",
        "sota",
        "arxiv",
        "research",
        "model",
        "training",
        "inference",
        "agent",
        "gemma",
        "flux",
    ]
    return any(kw in text_lower for kw in keywords)


# Backward compatibility aliases
async def fetch_twitter_posts(accounts: List[str] = None) -> List[dict]:
    return await fetch_twitter(accounts)


async def fetch_reddit_posts(subreddits: List[str] = None) -> List[dict]:
    return await fetch_reddit(subreddits)
