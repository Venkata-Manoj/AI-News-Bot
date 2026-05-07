"""Test script for Twitter + Reddit scraping (direct, no API key needed)."""

import asyncio
import sys

sys.path.insert(0, ".")

import config
from modules import apify_fetcher


async def test_twitter():
    """Test Twitter scraping via Nitter RSS."""
    print("\n" + "=" * 50)
    print("Testing Twitter (Nitter RSS)")
    print("=" * 50)

    try:
        tweets = await apify_fetcher.fetch_twitter(config.TWITTER_ACCOUNTS)
        print(f"✅ Fetched {len(tweets)} tweets")

        for i, tweet in enumerate(tweets[:3], 1):
            print(f"\n--- Tweet {i} ---")
            print(f"Text: {tweet.get('text', '')[:100]}...")
            print(f"URL: {tweet.get('url', 'N/A')}")

        return tweets
    except Exception as e:
        print(f"❌ Twitter failed: {e}")
        import traceback

        traceback.print_exc()
        return []


async def test_reddit():
    """Test Reddit scraping via direct JSON API."""
    print("\n" + "=" * 50)
    print("Testing Reddit (Direct JSON API)")
    print("=" * 50)

    try:
        posts = await apify_fetcher.fetch_reddit(config.REDDIT_SUBREDDITS)
        print(f"✅ Fetched {len(posts)} posts")

        for i, post in enumerate(posts[:3], 1):
            print(f"\n--- Post {i} ---")
            print(f"Title: {post.get('title', '')[:80]}...")
            print(f"Subreddit: {post.get('source', 'N/A')}")
            print(f"URL: {post.get('url', 'N/A')}")

        return posts
    except Exception as e:
        print(f"❌ Reddit failed: {e}")
        import traceback

        traceback.print_exc()
        return []


async def test_ai_filter():
    """Test AI content filter."""
    print("\n" + "=" * 50)
    print("Testing AI Content Filter")
    print("=" * 50)

    test_cases = [
        ("Just released GPT-5!", True),
        ("Beautiful sunset today", False),
        ("New ML model beats SOTA", True),
        ("Dinner at 7pm", False),
        ("OpenAI announces new LLM", True),
    ]

    for text, expected in test_cases:
        result = apify_fetcher.is_ai_related(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text[:30]}...' -> {result}")


async def main():
    print("=" * 50)
    print("Social Media Scraper Test")
    print("(Twitter RSS + Reddit JSON API)")
    print("=" * 50)

    print(f"\nTwitter: {config.TWITTER_ACCOUNTS}")
    print(f"Reddit: {config.REDDIT_SUBREDDITS}")

    # Test AI filter
    await test_ai_filter()

    # Test fetchers
    tweets = await test_twitter()
    posts = await test_reddit()

    # Summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Twitter: {len(tweets)} tweets")
    print(f"Reddit: {len(posts)} posts")
    print(f"Total: {len(tweets) + len(posts)} items")

    if tweets + posts:
        print("\n✅ Social media integration working!")


if __name__ == "__main__":
    asyncio.run(main())
