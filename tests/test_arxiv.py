"""Test arXiv fetcher — fetches 2 papers from 1 category."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.fetcher import fetch_arxiv


async def test_arxiv():
    print("=" * 60)
    print("TEST: arXiv Fetcher")
    print("Category: cs.AI, Limit: 2")
    print("=" * 60)

    articles = await fetch_arxiv(categories=["cs.AI"], max_results=2)

    print(f"\nResults: {len(articles)} papers")
    print("-" * 60)

    for i, a in enumerate(articles, 1):
        print(f"\n[{i}] {a.title[:80]}")
        print(f"    Source:    {a.source}")
        print(f"    URL:       {a.url[:80]}")
        print(f"    Body:      {a.body[:120]}..." if a.body else "    Body:      (empty)")
        print(f"    Published: {a.published}")

    print(f"\n{'=' * 60}")
    status = "PASSED" if len(articles) > 0 else "FAILED (0 papers)"
    print(f"ARXIV TEST: {status}")
    print(f"{'=' * 60}")
    return len(articles) > 0


if __name__ == "__main__":
    asyncio.run(test_arxiv())
