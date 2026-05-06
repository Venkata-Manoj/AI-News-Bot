import asyncio
import hashlib
import json
from datetime import datetime
from typing import List, Optional

import aiohttp
import feedparser
import httpx
from bs4 import BeautifulSoup

import config


def strip_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    return soup.get_text(separator=" ", strip=True)


def normalise_url(url: str) -> str:
    if not url:
        return ""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def hash_url(url: str) -> str:
    return hashlib.md5(normalise_url(url).encode()).hexdigest()


def extract_rss_text(entry) -> str:
    if hasattr(entry, "summary"):
        text = strip_html(entry.summary)
    elif hasattr(entry, "description"):
        text = strip_html(entry.description)
    elif hasattr(entry, "content"):
        content = entry.content[0].value if entry.content else ""
        text = strip_html(content)
    else:
        text = ""
    return text[:400]


class Article:
    def __init__(
        self, title, url, body, source, published: datetime = None, score: int = 0
    ):
        self.title = title
        self.url = normalise_url(url)
        self.body = body
        self.source = source
        self.published = published or datetime.utcnow()
        self.score = score
        self.url_hash = hash_url(self.url)


async def fetch_rss_feed(
    session: aiohttp.ClientSession, feed_url: str, source_name: str
) -> List[Article]:
    articles = []
    try:
        async with session.get(
            feed_url, timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status != 200:
                return []
            text = await response.text()
            feed = feedparser.parse(text)
            for entry in feed.entries[:10]:
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                articles.append(
                    Article(
                        title=entry.get("title", "Untitled").strip(),
                        url=entry.get("link", ""),
                        body=extract_rss_text(entry),
                        source=source_name,
                        published=pub_date,
                    )
                )
    except Exception:
        pass
    return articles


async def fetch_all_rss(feed_urls: List[str]) -> List[Article]:
    articles = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in feed_urls:
            try:
                from urllib.parse import urlparse

                parsed = urlparse(url)
                name = parsed.netloc.replace("www.", "").split(".")[0]
            except:
                name = "unknown"
            tasks.append(fetch_rss_feed(session, url, name))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                articles.extend(result)
    print(f"[RSS] Fetched {len(articles)} articles from {len(feed_urls)} feeds")
    return articles


async def fetch_hackernews(tag: str = "ai", limit: int = 10) -> List[Article]:
    articles = []
    try:
        async with aiohttp.ClientSession() as session:
            search_url = "https://hn.algolia.com/api/v1/search_by_date"
            params = {"query": tag, "tags": "story", "hits": limit * 2, "daysAgo": 1}
            async with session.get(
                search_url, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                for hit in data.get("hits", [])[:limit]:
                    url = (
                        hit.get("url")
                        or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                    )
                    articles.append(
                        Article(
                            title=hit.get("title", "")[:200],
                            url=url,
                            body="",
                            source="HackerNews",
                            published=datetime.fromtimestamp(
                                hit.get("created_at_i", 0)
                            ),
                        )
                    )
    except Exception as e:
        print(f"[HN] Error: {e}")
    print(f"[HN] Fetched {len(articles)} articles")
    return articles


async def fetch_arxiv(
    categories: List[str] = None, max_results: int = 10
) -> List[Article]:
    articles = []
    if categories is None:
        categories = ["cs.AI", "cs.CL", "cs.LG"]
    base_url = "http://export.arxiv.org/api/query"
    for cat in categories[:2]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "search_query": f"cat:{cat}",
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": max_results // 2,
                }
                async with session.get(
                    base_url, params=params, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        continue
                    text = await resp.text()
                    feed = feedparser.parse(text)
                    for entry in feed.entries[: max_results // 2]:
                        articles.append(
                            Article(
                                title=entry.get("title", "").strip().replace("\n", " "),
                                url=entry.get("id", ""),
                                body=entry.get("summary", "")[:400],
                                source=f"arXiv:{cat}",
                                published=datetime(*entry.published_parsed[:6])
                                if entry.published_parsed
                                else datetime.utcnow(),
                            )
                        )
        except Exception as e:
            print(f"[arXiv] Error: {e}")
    print(f"[arXiv] Fetched {len(articles)} papers")
    return articles


async def fetch_all(options: dict = None) -> List[Article]:
    """Fetch from all enabled sources."""
    if options is None:
        options = config.FETCH_OPTIONS
    articles = []
    tasks = []

    if options.get("rss", True):
        tasks.append(fetch_all_rss(config.RSS_FEEDS))
    if options.get("hn", True):
        tasks.append(fetch_hackernews("ai", 10))
    if options.get("arxiv", True):
        tasks.append(fetch_arxiv(["cs.AI", "cs.LG", "cs.CL"], 10))

    # Apify: Twitter + Reddit
    if options.get("apify_twitter") or options.get("apify_reddit"):
        tasks.append(fetch_apify_sources(options))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, list):
            articles.extend(result)
    articles.sort(key=lambda a: (a.score or 0, a.published), reverse=True)
    print(f"[Total] Fetched {len(articles)} articles from all sources")
    return articles


async def fetch_apify_sources(options: dict) -> List[Article]:
    """Fetch from Apify (Twitter + Reddit)."""
    articles = []

    if not config.APIFY_API_KEY:
        print("[Apify] API key not set, skipping...")
        return articles

    try:
        from modules.apify_fetcher import ApifyFetcher

        async with ApifyFetcher() as fetcher:
            if options.get("apify_twitter"):
                try:
                    tweets = await fetcher.fetch_twitter(config.TWITTER_ACCOUNTS)
                    for tweet in tweets:
                        articles.append(
                            Article(
                                title=tweet.get("text", "")[:100],
                                url=tweet.get("url", ""),
                                body=tweet.get("text", ""),
                                source="twitter",
                                published=datetime.fromisoformat(
                                    tweet.get(
                                        "timestamp", datetime.utcnow().isoformat()
                                    )
                                )
                                if tweet.get("timestamp")
                                else datetime.utcnow(),
                            )
                        )
                    print(f"[Apify] Twitter: {len(tweets)} relevant tweets")
                except Exception as e:
                    print(f"[Apify] Twitter error: {e}")

            if options.get("apify_reddit"):
                try:
                    posts = await fetcher.fetch_reddit(config.REDDIT_SUBREDDITS)
                    for post in posts:
                        articles.append(
                            Article(
                                title=post.get("title", "")[:100],
                                url=post.get("url", ""),
                                body=post.get("body", "") or post.get("text", ""),
                                source=f"r/{post.get('subreddit', 'unknown')}",
                                published=datetime.fromisoformat(
                                    post.get("created", datetime.utcnow().isoformat())
                                )
                                if post.get("created")
                                else datetime.utcnow(),
                            )
                        )
                    print(f"[Apify] Reddit: {len(posts)} relevant posts")
                except Exception as e:
                    print(f"[Apify] Reddit error: {e}")

    except Exception as e:
        print(f"[Apify] Fetch error: {e}")

    return articles
