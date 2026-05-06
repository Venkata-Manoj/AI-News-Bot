import json
import hashlib
import os
from datetime import datetime
from typing import List, Dict

import config
from modules.fetcher import Article


def load_seen_urls() -> Dict[str, str]:
    try:
        with open(config.SEEN_URLS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_seen_urls(seen_urls: Dict[str, str]):
    os.makedirs(config.DATA_DIR, exist_ok=True)

    if len(seen_urls) > 5000:
        sorted_urls = sorted(seen_urls.items(), key=lambda x: x[1])
        seen_urls = dict(sorted_urls[-4000:])

    with open(config.SEEN_URLS_FILE, "w") as f:
        json.dump(seen_urls, f)


def hash_url(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return hashlib.md5(clean_url.encode()).hexdigest()


def is_seen(url_hash: str) -> bool:
    seen_urls = load_seen_urls()
    return url_hash in seen_urls


def mark_seen(url_hash: str):
    seen_urls = load_seen_urls()
    seen_urls[url_hash] = datetime.utcnow().isoformat()
    save_seen_urls(seen_urls)


def filter_new(articles: List[Article]) -> List[Article]:
    seen_urls = load_seen_urls()
    new_articles = []

    for article in articles:
        if article.url_hash not in seen_urls:
            new_articles.append(article)
        else:
            pass

    return new_articles


def filter_by_keywords(
    articles: List[Article], keywords: List[str] = None
) -> List[Article]:
    if keywords is None:
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
            "gemma",
            "mistral",
            "llama",
            "Stable Diffusion",
            "hugging face",
            "model",
            "benchmark",
            "sota",
            "arxiv",
        ]

    import re

    filtered = []
    pattern = re.compile("|".join(keywords), re.IGNORECASE)

    for article in articles:
        text = f"{article.title} {article.body}"
        if pattern.search(text):
            filtered.append(article)

    return filtered
