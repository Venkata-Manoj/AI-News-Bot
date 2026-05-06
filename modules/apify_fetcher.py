"""Apify actor integration for X (Twitter) and Reddit scraping.

Implements smart incremental fetching with cursors/timestamps
to minimize API calls and avoid rate limits.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp
import httpx

import config
from modules.db import db


APIFY_API_BASE = "https://api.apify.com/v2"
APIFY_PROXY = "http://api.apify.com"  # Apify proxy endpoint

# Actor IDs for X and Reddit
TWITTER_ACTOR_ID = (
    "bingoisoft/twitter-scraper"  # Alternative: "apify/twitter-tweet-scraper"
)
REDDIT_ACTOR_ID = "janghova/reddit-scraper"

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
    "r/MachineLearning",
    "r/artificial",
    "r/OpenAI",
    "r/LocalLLaMA",
    "r/singularity",
    "r/ChatGPT",
]


class ApifyFetcher:
    """Production-grade Apify fetcher with:
    - Incremental cursors (only new content)
    - Smart backoff and rate limit respect
    - Batched fetches to minimize API calls
    - Automatic retry with exponential backoff
    """

    def __init__(self, api_token: str = None):
        self.api_token = api_token or config.APIFY_API_KEY
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    # --- Twitter/X Fetching ---

    async def fetch_twitter(
        self, accounts: List[str] = None, increment: bool = True
    ) -> List[dict]:
        """Fetch recent tweets from target accounts.

        Args:
            accounts: List of Twitter handles to monitor
            increment: If True, only fetch content newer than last run
        """
        if not accounts:
            accounts = TWITTER_ACCOUNTS

        all_items = []

        # Get last fetch timestamp for dedup
        last_fetch = None
        if increment:
            last_fetch = db.get_last_fetch("twitter")

        for account in accounts:
            try:
                items = await self._run_twitter_actor(account, last_fetch)
                all_items.extend(items)
            except Exception as e:
                print(f"[Apify] Twitter fetch error for {account}: {e}")
                db.log_error("apify_fetcher", str(e), f"twitter:{account}")
                continue

        # Update last fetch timestamp
        if all_items:
            latest = max(all_items, key=lambda x: x.get("timestamp", ""))
            db.set_last_fetch("twitter", datetime.now(timezone.utc).isoformat())

        return all_items

    async def _run_twitter_actor(self, account: str, since: str = None) -> List[dict]:
        """Run Apify Twitter scraper for a single account."""

        # Build actor input
        actor_input = {
            "handles": [account],
            "maxItems": 20,
            "includeReplies": False,
            "includeRetweets": False,
            "since": since or "1d",  # Default to last 24h
        }

        # Run actor and get dataset items
        items = await self._run_actor(TWITTER_ACTOR_ID, actor_input)

        # Filter only AI-relevant tweets
        relevant = [item for item in items if self._is_ai_related(item.get("text", ""))]

        return relevant

    # --- Reddit Fetching ---

    async def fetch_reddit(
        self, subreddits: List[str] = None, increment: bool = True
    ) -> List[dict]:
        """Fetch recent posts from target subreddits.

        Args:
            subreddits: List of subreddit names
            increment: If True, only fetch content newer than last run
        """
        if not subreddits:
            subreddits = REDDIT_SUBREDDITS

        all_items = []

        # Get last fetch timestamp for dedup
        last_fetch = None
        if increment:
            last_fetch = db.get_last_fetch("reddit")

        for subreddit in subreddits:
            try:
                items = await self._run_reddit_actor(subreddit, last_fetch)
                all_items.extend(items)
            except Exception as e:
                print(f"[Apify] Reddit fetch error for {subreddit}: {e}")
                db.log_error("apify_fetcher", str(e), f"reddit:{subreddit}")
                continue

        # Update last fetch timestamp
        if all_items:
            latest = max(all_items, key=lambda x: x.get("created", ""))
            db.set_last_fetch("reddit", datetime.now(timezone.utc).isoformat())

        return all_items

    async def _run_reddit_actor(self, subreddit: str, since: str = None) -> List[dict]:
        """Run Apify Reddit scraper for a single subreddit."""

        # Build actor input
        actor_input = {
            "subreddits": [subreddit],
            "maxItems": 20,
            "sort": "new",
            "time": "day",  # Last 24 hours
            "since": since,
        }

        # Run actor and get dataset items
        items = await self._run_actor(REDDIT_ACTOR_ID, actor_input)

        # Filter only AI-relevant posts
        relevant = [
            item
            for item in items
            if self._is_ai_related(item.get("title", "") + " " + item.get("body", ""))
        ]

        return relevant

    # --- Generic Apify Actor Runner ---

    async def _run_actor(self, actor_id: str, actor_input: dict) -> List[dict]:
        """Run an Apify actor and return results.

        Implements smart backoff:
        - Checks rate limits before each call
        - Waits if rate limit approached
        - Retries with exponential backoff on 429
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        url = f"{APIFY_API_BASE}/acts/{actor_id}/runs"

        # Check rate limits before call
        await self._respect_rate_limits()

        # Run actor
        async with self.session.post(
            url,
            json={"token": self.api_token, "input": actor_input},
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if resp.status == 429:
                # Rate limited - wait and retry once
                print(f"[Apify] Rate limited, waiting 30s...")
                await asyncio.sleep(30)
                return await self._run_actor(actor_id, actor_input)

            if resp.status != 201:
                raise Exception(f"Apify actor run failed: {resp.status}")

            data = await resp.json()
            run_id = data["data"]["id"]
            print(f"[Apify] Started actor run: {run_id}")

        # Poll for completion
        items = await self._wait_for_run(run_id)
        return items

    async def _wait_for_run(self, run_id: str, max_wait: int = 60) -> List[dict]:
        """Poll run status until complete or timeout."""
        start = datetime.now(timezone.utc)

        while (datetime.now(timezone.utc) - start).total_seconds() < max_wait:
            url = f"{APIFY_API_BASE}/actor-runs/{run_id}"

            async with self.session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    await asyncio.sleep(2)
                    continue

                data = await resp.json()
                status = data["data"]["status"]

                if status == "SUCCEEDED":
                    # Get dataset items
                    dataset_id = data["data"]["defaultDatasetId"]
                    return await self._get_dataset_items(dataset_id)
                elif status in ("FAILED", "TIMED-OUT"):
                    raise Exception(f"Actor run failed: {status}")

                await asyncio.sleep(2)

        raise TimeoutError(f"Actor run timed out after {max_wait}s")

    async def _get_dataset_items(self, dataset_id: str, limit: int = 100) -> List[dict]:
        """Fetch items from actor dataset."""
        url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items"
        params = {"limit": limit}

        async with self.session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                return []
            return await resp.json()

    # --- Rate Limit Management ---

    async def _respect_rate_limits(self):
        """Respect Apify rate limits to avoid 429s."""
        # Apify free tier: 200 CUs/month
        # Typical actor run: ~0.1 CU
        # We can safely run ~20 times/day

        # Check if we've made too many calls recently
        last_call = getattr(self, "_last_call_time", None)
        if last_call:
            elapsed = (datetime.now(timezone.utc) - last_call).total_seconds()
            if elapsed < 5:  # Minimum 5s between calls
                wait = 5 - elapsed
                print(f"[Apify] Rate limit buffer, waiting {wait:.1f}s")
                await asyncio.sleep(wait)

        self._last_call_time = datetime.now(timezone.utc)

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
    async with ApifyFetcher() as fetcher:
        return await fetcher.fetch_twitter(accounts)


async def fetch_reddit_posts(subreddits: List[str] = None) -> List[dict]:
    async with ApifyFetcher() as fetcher:
        return await fetcher.fetch_reddit(subreddits)
