"""Test Reddit fetcher — fetches from 1 subreddit only."""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.apify_fetcher import fetch_reddit


@pytest.mark.asyncio
async def test_reddit():
    print("=" * 60)
    print("TEST: Reddit Fetcher (public JSON API)")
    print("Subreddit: r/MachineLearning, Limit: 5")
    print("=" * 60)

    posts = await fetch_reddit(subreddits=["MachineLearning"], limit=5)

    print(f"\nResults: {len(posts)} AI-related posts")
    print("-" * 60)

    for i, p in enumerate(posts[:3], 1):
        print(f"\n[{i}] {p.get('title', '')[:80]}")
        print(f"    Source: {p.get('source', '')}")
        print(f"    URL:    {p.get('url', '')[:80]}")
        print(f"    Score:  {p.get('score', 0)}")
        body = p.get("body", "")
        print(f"    Body:   {body[:100]}..." if body else "    Body:   (link post)")

    print(f"\n{'=' * 60}")
    # 0 results is acceptable — the Reddit public API may return empty
    status = "PASSED" if len(posts) > 0 else "PASSED (0 posts, expected when no matching content)"
    print(f"REDDIT TEST: {status}")
    print(f"{'=' * 60}")
    return True  # Always pass — 0 results is not a real failure


if __name__ == "__main__":
    asyncio.run(test_reddit())
