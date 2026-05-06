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
        tweets = await apify_fetcher.fetch_twitter_posts(config.TWITTER_ACCOUNTS)
        print(f"✅ Fetched {len(tweets)} tweets")

        if tweets:
            for i, tweet in enumerate(tweets[:5], 1):
                print(f"\n--- Tweet {i} ---")
                print(f"Text: {tweet.get('text', '')[:150]}...")
                print(f"URL: {tweet.get('url', 'N/A')}")
                print(f"User: {tweet.get('username', 'N/A')}")
        else:
            print("⚠️ No tweets returned")

        return tweets
    except Exception as e:
        print(f"❌ Twitter fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return []


async def test_reddit():
    """Test Reddit scraping via direct JSON API."""
    print("\n" + "=" * 50)
    print("Testing Reddit (Direct JSON API)")
    print("=" * 50)

    try:
        posts = await apify_fetcher.fetch_reddit_posts(config.REDDIT_SUBREDDITS)
        print(f"✅ Fetched {len(posts)} posts")

        if posts:
            for i, post in enumerate(posts[:5], 1):
                print(f"\n--- Post {i} ---")
                print(f"Title: {post.get('title', '')[:100]}...")
                print(f"Subreddit: r/{post.get('subreddit', 'N/A')}")
                print(f"URL: {post.get('url', 'N/A')}")
                print(f"Score: {post.get('score', 'N/A')}")
        else:
            print("⚠️ No posts returned")

        return posts
    except Exception as e:
        print(f"❌ Reddit fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return []


async def test_direct_fetcher():
    """Test the DirectFetcher class directly."""
    print("\n" + "=" * 50)
    print("Testing DirectFetcher class")
    print("=" * 50)

    async with apify_fetcher.DirectFetcher() as fetcher:
        # Test Twitter
        print("\n--- Twitter ---")
        try:
            tweets = await fetcher.fetch_twitter(["sama", "elonmusk"])
            print(f"✅ {len(tweets)} tweets")
        except Exception as e:
            print(f"❌ {e}")

        # Test Reddit
        print("\n--- Reddit ---")
        try:
            posts = await fetcher.fetch_reddit(["MachineLearning", "artificial"])
            print(f"✅ {len(posts)} posts")
        except Exception as e:
            print(f"❌ {e}")


async def main():
    print("=" * 50)
    print("Twitter + Reddit Scraper Test")
    print("(Direct scraping - no API key needed)")
    print("=" * 50)

    print(f"\nTwitter accounts: {config.TWITTER_ACCOUNTS}")
    print(f"Reddit subreddits: {config.REDDIT_SUBREDDITS}")

    # Test DirectFetcher class
    await test_direct_fetcher()

    # Test convenience functions
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
    else:
        print("\n❌ No data - check errors above")


if __name__ == "__main__":
    asyncio.run(main())
