import re
from datetime import datetime, timedelta, timezone


def escape_md(text: str) -> str:
    if not text:
        return ""
    # Only escape special chars that break MarkdownV2
    return (
        text.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def format_article(article, summary: str) -> str:
    title = escape_md(article.title[:100])
    summary = escape_md(summary[:200])  # Limit summary

    # Convert source to readable format
    source = (
        article.source.replace("r/", "r/")
        .replace("HackerNews", "HN")
        .replace("arXiv:", "arXiv ")
    )

    # IST timestamp
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_now = datetime.now(ist_offset)
    timestamp = ist_now.strftime("%H:%M IST")

    url = article.url

    # Cleaner format: Title, Summary, "Read here", Timestamp
    message = f"""{title}

{summary}

[Read here]({url})
{timestamp} | {source}"""

    return message


def format_youtube_article(article, summary: str) -> str:
    """Format a YouTube video for Telegram with rich metadata."""
    yt = getattr(article, "youtube_data", None)
    if not yt:
        return format_article(article, summary)

    title = escape_md(article.title[:100])
    summary = escape_md(summary[:250])

    # IST timestamp
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_now = datetime.now(ist_offset)
    timestamp = ist_now.strftime("%H:%M IST")

    # Stats line
    stats_parts = []
    if yt.get("views_display"):
        stats_parts.append(f"{yt['views_display']} views")
    if yt.get("likes_display"):
        stats_parts.append(f"{yt['likes_display']} likes")
    if yt.get("duration_display"):
        stats_parts.append(yt["duration_display"])
    stats_line = " · ".join(stats_parts)

    # Tags line (max 4 tags)
    tags = yt.get("tags", [])[:4]
    tags_line = " ".join(f"#{escape_md(t.replace(' ', ''))}" for t in tags) if tags else ""

    # Top comment
    comment_line = ""
    top_comment = yt.get("top_comment")
    if top_comment and top_comment.get("text"):
        # Strip HTML from comment, truncate
        comment_text = re.sub(r"<[^>]+>", "", top_comment["text"])
        comment_text = escape_md(comment_text[:120])
        author = escape_md(top_comment.get("author", "")[:30])
        likes = top_comment.get("like_count", 0)
        comment_line = f'\n💬 "{comment_text}" — {author}'
        if likes > 0:
            comment_line += f" ({likes} 👍)"

    # Channel name
    channel = escape_md(yt.get("channel_title", ""))

    # Build message
    lines = [f"🎬 {title}"]

    if channel:
        lines.append(f"📺 {channel}")

    lines.append(f"\n📝 {summary}")

    if stats_line:
        lines.append(f"\n📊 {stats_line}")

    if tags_line:
        lines.append(f"🏷️ {tags_line}")

    if comment_line:
        lines.append(comment_line)

    lines.append(f"\n🔗 Watch: {article.url}")
    lines.append(f"⏰ {timestamp} | youtube")

    return "\n".join(lines)


def format_batch(articles_summaries: list) -> list[str]:
    messages = []

    for item in articles_summaries:
        article = item.get("article")
        summary = item.get("summary", "")

        if article and summary:
            # Route to YouTube-specific formatter when appropriate
            if getattr(article, "source", "") == "youtube":
                message = format_youtube_article(article, summary)
            else:
                message = format_article(article, summary)
            messages.append(message)

    return messages
