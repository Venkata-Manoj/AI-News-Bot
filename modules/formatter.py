"""Telegram message formatting with structured, visually clear output."""

import re
from datetime import datetime, timedelta, timezone

# Source emoji mapping for quick visual scanning
SOURCE_EMOJI = {
    # AI Labs & Companies
    "openai": "🤖",
    "anthropic": "🧠",
    "google": "🔬",
    "deepmind": "🔬",
    "huggingface": "🤗",
    "mistral": "🌬️",
    "meta": "📘",
    "cohere": "🟢",
    "stability": "🎨",
    # Tech Media
    "techcrunch": "📰",
    "venturebeat": "📰",
    "theverge": "📰",
    "technology review": "📰",
    "wired": "📰",
    "arstechnica": "📰",
    "marktechpost": "📰",
    "the-decoder": "📰",
    # Platforms
    "github": "🐙",
    "reddit": "💬",
    "hackernews": "🎯",
    "hn": "🎯",
    "twitter": "🐦",
    "x": "🐦",
    "youtube": "▶️",
    "arxiv": "📄",
    # Generic
    "nvidia": "🟢",
    "xai": "⚡",
}

# Source category colors (represented as emoji)
SOURCE_CATEGORIES = {
    "company": "🏢",
    "media": "📡",
    "research": "🔬",
    "social": "💬",
    "video": "▶️",
    "unknown": "📌",
}

SEPARATOR = "━" * 30


def escape_md(text: str) -> str:
    """Escape MarkdownV2 special characters for Telegram."""
    if not text:
        return ""
    return (
        text.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def get_source_emoji(source: str) -> str:
    """Get appropriate emoji for a source name."""
    if not source:
        return "📌"

    source_lower = source.lower().strip()

    # Direct match first
    for key, emoji in SOURCE_EMOJI.items():
        if key in source_lower:
            return emoji

    # Categorize by source type
    if source_lower.startswith("r/"):
        return "💬"
    if "arxiv" in source_lower:
        return "📄"
    if source_lower == "youtube":
        return "▶️"

    return "📌"


def get_source_label(source: str) -> str:
    """Get a clean readable label for the source."""
    if not source:
        return "source"

    s = source.replace("arXiv:", "arXiv ")
    s = s.replace("r/", "r/")
    s = s.replace("HackerNews", "HN")

    # Handle RSS feed titles
    if "/" in s and not s.startswith("r/"):
        parts = s.split("/")
        s = parts[-1] if parts[-1] else parts[-2]

    # Clean up common platforms
    s = s.replace("www.", "").strip()

    return s[:30]


def format_batch_header(
    count: int, sources: list[str], timestamp: str | None = None
) -> str:
    """Create a batch header message for the start of a delivery run."""
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_now = datetime.now(ist_offset)
    time_str = timestamp or ist_now.strftime("%d %b %H:%M")

    # Get unique source emojis for the header
    source_emojis = list(
        dict.fromkeys(get_source_emoji(s) for s in sources if s)
    )
    emoji_str = " ".join(source_emojis) if source_emojis else "🤖"

    header = (
        f"{emoji_str} **AI News Brief — {time_str}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{count} storie{'s' if count != 1 else 'y'} this cycle"
    )
    return header


async def format_youtube_article(article, summary: str) -> str:
    """Format a YouTube video for Telegram with rich metadata."""
    yt = getattr(article, "youtube_data", None)
    if not yt:
        return format_article(article, summary)

    title = article.title[:120] if article.title else "Untitled"
    summary = summary[:300] if summary else ""

    # IST timestamp
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_now = datetime.now(ist_offset)
    timestamp = ist_now.strftime("%H:%M IST")

    # Stats line
    stats_parts = []
    if yt.get("views_display"):
        stats_parts.append(f"👁️ {yt['views_display']} views")
    if yt.get("likes_display"):
        stats_parts.append(f"👍 {yt['likes_display']}")
    if yt.get("duration_display"):
        stats_parts.append(f"⏱️ {yt['duration_display']}")
    stats_line = "  ".join(stats_parts)

    # Tags line (max 4)
    tags = yt.get("tags", [])[:4]
    tags_line = (
        "🏷️ " + " ".join(f"#{tag.replace(' ', '')}" for tag in tags)
        if tags
        else ""
    )

    # Top comment
    comment_line = ""
    top_comment = yt.get("top_comment")
    if top_comment and top_comment.get("text"):
        comment_text = re.sub(r"<[^>]+>", "", top_comment["text"])[:150]
        author = top_comment.get("author", "")[:30]
        likes = top_comment.get("like_count", 0)
        comment_line = f'💬 "{comment_text}" — {author}'
        if likes > 0:
            comment_line += f" ({likes} 👍)"

    channel = yt.get("channel_title", "")

    lines = ["▶️ **" + title + "**"]
    lines.append("")

    if channel:
        lines.append(f"📺 {channel}")

    lines.append(f"\n📝 {summary}")

    if stats_line:
        lines.append(f"\n{stats_line}")
    if tags_line:
        lines.append(f"\n{tags_line}")
    if comment_line:
        lines.append(f"\n{comment_line}")

    lines.append("")
    lines.append(f"🔗 [Watch on YouTube]({article.url})")
    lines.append(f"⏰ {timestamp}  ·  ▶️ youtube")

    return "\n".join(lines)


def format_article(article, summary: str) -> str:
    """Format an article for Telegram with structured output."""
    title = article.title[:120] if article.title else "Untitled"
    summary = summary[:300] if summary else ""

    # Source handling
    source = article.source or "unknown"
    emoji = get_source_emoji(source)
    label = get_source_label(source)

    # IST timestamp
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_now = datetime.now(ist_offset)
    timestamp = ist_now.strftime("%H:%M IST")

    url = article.url

    # Build structured message
    lines = [
        f"{emoji} **{title}**",
        "",
        f"{summary}",
        "",
        f"🔗 [Read full article]({url})",
        f"⏰ {timestamp}  ·  {emoji} {label}",
    ]

    return "\n".join(lines)


def format_batch(articles_summaries: list, include_header: bool = True) -> list[str]:
    """Format a batch of articles for sending. Optionally preprends a header."""
    messages = []

    # Collect sources for header
    sources = []

    for item in articles_summaries:
        article = item.get("article")
        summary = item.get("summary", "")

        if article and summary:
            if article.source:
                sources.append(article.source)

            if getattr(article, "source", "") == "youtube":
                message = format_youtube_article(article, summary)
            else:
                message = format_article(article, summary)

            messages.append(message)

    # Prepend batch header
    if include_header and messages:
        header = format_batch_header(len(messages), sources)
        messages.insert(0, header)

    return messages
