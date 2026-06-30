"""Test RSS feed fetcher — fetches from 2 feeds, prints results."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.fetcher import fetch_all_rss


async def test_rss():
    # Only 2 feeds to save bandwidth
    test_feeds = [
        "https://openai.com/blog/rss.xml",
        "https://huggingface.co/blog/feed.xml",
    ]

    print("=" * 60)
    print("TEST: RSS Feed Fetcher")
    print(f"Feeds: {len(test_feeds)}")
    print("=" * 60)

    articles = await fetch_all_rss(test_feeds)

    print(f"\nResults: {len(articles)} articles")
    print("-" * 60)

    for i, a in enumerate(articles[:3], 1):
        print(f"\n[{i}] {a.title[:80]}")
        print(f"    Source:    {a.source}")
        print(f"    URL:       {a.url[:80]}")
        print(f"    Body:      {a.body[:100]}..." if a.body else "    Body:      (empty)")
        print(f"    Published: {a.published}")
        print(f"    URL Hash:  {a.url_hash}")

    print(f"\n{'=' * 60}")
    status = "PASSED" if len(articles) > 0 else "FAILED (0 articles)"
    print(f"RSS TEST: {status}")
    print(f"{'=' * 60}")
    return len(articles) > 0


if __name__ == "__main__":
    asyncio.run(test_rss())
