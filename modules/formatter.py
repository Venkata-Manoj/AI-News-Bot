import re
from datetime import datetime, timezone, timedelta


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


def format_batch(articles_summaries: list) -> list[str]:
    messages = []

    for item in articles_summaries:
        article = item.get("article")
        summary = item.get("summary", "")

        if article and summary:
            message = format_article(article, summary)
            messages.append(message)

    return messages
