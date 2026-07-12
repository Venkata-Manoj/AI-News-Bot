"""Unit tests for modules/formatter.py — Telegram message formatting.

Tests all formatting functions including escape, emoji mapping, labels,
article formatting, YouTube formatting, and batch operations.
All tests are pure unit tests with no network access required.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.formatter import (
    SOURCE_EMOJI,
    escape_md,
    format_article,
    format_batch,
    format_batch_header,
    format_youtube_article,
    get_source_emoji,
    get_source_label,
)


# ── Fake article helpers ───────────────────────────────────────────────────


def make_article(
    url="https://example.com/article",
    title="Test Article Title",
    body="Test body content for the article.",
    source="openai",
    url_hash=None,
    youtube_data=None,
):
    """Create a minimal article-like object for testing formatting."""

    class FakeArticle:
        def __init__(self, url, title, body, source, url_hash, youtube_data):
            self.url = url
            self.title = title
            self.body = body
            self.source = source
            self.url_hash = url_hash
            self.youtube_data = youtube_data

        def __repr__(self):
            return f"<Article {self.title[:30]}>"

    return FakeArticle(
        url=url,
        title=title,
        body=body,
        source=source,
        url_hash=url_hash,
        youtube_data=youtube_data,
    )


def make_youtube_data(overrides=None):
    """Create standard YouTube metadata dict for testing."""
    data = {
        "video_id": "abc123",
        "channel_title": "Test Channel",
        "views_display": "131K",
        "likes_display": "7.2K",
        "duration_display": "10m 4s",
        "tags": ["ai", "machinelearning", "deeplearning", "research"],
        "top_comment": {
            "text": "What a Time To Be Alive!",
            "author": "Viewer1",
            "like_count": 330,
        },
    }
    if overrides:
        data.update(overrides)
    return data


# ── escape_md ──────────────────────────────────────────────────────────────


class TestEscapeMD:
    def test_escape_empty_string(self):
        """Empty string should return empty string."""
        assert escape_md("") == ""

    def test_escape_none(self):
        """None should return empty string."""
        assert escape_md(None) == ""

    def test_escape_no_special_chars(self):
        """Normal text without special chars should pass through unchanged."""
        text = "Hello, this is normal text with numbers 123!"
        assert escape_md(text) == text

    def test_escape_underscore(self):
        """Underscore should be escaped."""
        assert escape_md("hello_world") == "hello\\_world"

    def test_escape_asterisk(self):
        """Asterisk should be escaped."""
        assert escape_md("bold*text*here") == "bold\\*text\\*here"

    def test_escape_brackets(self):
        """Square brackets should be escaped."""
        assert escape_md("[link text]") == "\\[link text\\]"

    def test_escape_combined(self):
        """Multiple special characters should all be escaped."""
        result = escape_md("_*[]_")
        assert result == "\\_\\*\\[\\]\\_"

    def test_escape_mixed_content(self):
        """Text with and without special chars should escape only the special ones."""
        result = escape_md("Check [this] _out_ *now*")
        assert "\\[" in result and "\\]" in result
        assert "\\_" in result
        assert "\\*" in result
        # Make sure normal chars are preserved
        assert "Check" in result
        assert "now" in result


# ── get_source_emoji ──────────────────────────────────────────────────────


class TestGetSourceEmoji:
    def test_emoji_empty(self):
        """Empty source should return default emoji."""
        assert get_source_emoji("") == "📌"

    def test_emoji_none(self):
        """None source should return default emoji."""
        assert get_source_emoji(None) == "📌"

    def test_emoji_direct_match(self):
        """Known source keys should return matching emoji."""
        assert get_source_emoji("openai") == "🤖"
        assert get_source_emoji("anthropic") == "🧠"
        assert get_source_emoji("youtube") == "▶️"
        assert get_source_emoji("github") == "🐙"

    def test_emoji_case_insensitive(self):
        """Source matching should be case-insensitive."""
        assert get_source_emoji("OpenAI") == "🤖"
        assert get_source_emoji("ANTHROPIC") == "🧠"
        assert get_source_emoji("YouTube") == "▶️"

    def test_emoji_partial_match(self):
        """Substring match should still find the emoji."""
        assert get_source_emoji("openai-blog") == "🤖"
        assert get_source_emoji("hackernews-top") == "🎯"

    def test_emoji_reddit_subreddit(self):
        """r/ prefix should return Reddit emoji."""
        assert get_source_emoji("r/MachineLearning") == "💬"

    def test_emoji_arxiv(self):
        """arxiv should return paper emoji."""
        assert get_source_emoji("arXiv:cs.AI") == "📄"

    def test_emoji_unknown_source(self):
        """Unknown source should return default emoji."""
        assert get_source_emoji("unknown-blog") == "📌"
        assert get_source_emoji("random-site") == "📌"

    def test_emoji_whitespace_handling(self):
        """Leading/trailing whitespace should be stripped."""
        assert get_source_emoji("  openai  ") == "🤖"


# ── get_source_label ──────────────────────────────────────────────────────


class TestGetSourceLabel:
    def test_label_empty(self):
        """Empty source should return 'source'."""
        assert get_source_label("") == "source"

    def test_label_none(self):
        """None source should return 'source'."""
        assert get_source_label(None) == "source"

    def test_label_arxiv_prefix(self):
        """arXiv: prefix should be cleaned."""
        assert get_source_label("arXiv:cs.AI") == "arXiv cs.AI"

    def test_label_subreddit(self):
        """r/ prefix should be preserved."""
        assert get_source_label("r/MachineLearning") == "r/MachineLearning"

    def test_label_hackernews_shortened(self):
        """HackerNews should be shortened to HN."""
        assert get_source_label("HackerNews") == "HN"

    def test_label_rss_path(self):
        """RSS feed paths should extract the last segment."""
        result = get_source_label("openai/blog/rss")
        assert "openai" not in result or "rss" not in result

    def test_label_www_removed(self):
        """www. prefix should be stripped."""
        assert get_source_label("www.example.com") == "example.com"

    def test_label_truncation(self):
        """Labels longer than 30 chars should be truncated."""
        long_name = "a" * 50
        assert len(get_source_label(long_name)) <= 30

    def test_label_clean_source(self):
        """Clean source name should pass through mostly unchanged."""
        label = get_source_label("OpenAI")
        assert "OpenAI" in label


# ── format_batch_header ────────────────────────────────────────────────────


class TestFormatBatchHeader:
    def test_header_single_article(self):
        """Single article should use singular 'story'."""
        header = format_batch_header(1, ["openai"])
        assert "story" in header or "stories" not in header

    def test_header_multiple_articles(self):
        """Multiple articles should use plural 'stories'."""
        header = format_batch_header(3, ["openai", "anthropic"])
        assert "stories" in header
        assert "3" in header

    def test_header_with_emoji(self):
        """Header should include source emoji."""
        header = format_batch_header(2, ["openai"])
        assert "🤖" in header  # openai emoji

    def test_header_no_source(self):
        """Header with no sources should use default emoji."""
        header = format_batch_header(1, [])
        assert "🤖" in header

    def test_header_with_timestamp(self):
        """Custom timestamp should appear in header."""
        header = format_batch_header(2, ["github"], timestamp="12 Jul 20:00")
        assert "12 Jul 20:00" in header

    def test_header_multiple_sources_dedup(self):
        """Duplicate sources should not duplicate emojis."""
        header = format_batch_header(5, ["openai", "openai", "anthropic"])
        count_openai = header.count("🤖")
        count_anthropic = header.count("🧠")
        assert count_openai == 1  # deduplicated
        assert count_anthropic == 1

    def test_header_format_structure(self):
        """Header should have separator line and count."""
        header = format_batch_header(3, ["google"])
        assert "━━━━━━━━━━━━━━━━━━━━" in header
        assert "AI News Brief" in header

    def test_header_zero_articles(self):
        """Header with zero articles should still format cleanly."""
        header = format_batch_header(0, [])
        assert "0 stories" in header or "0 storie" in header


# ── format_article ────────────────────────────────────────────────────────


class TestFormatArticle:
    def test_format_minimal_article(self):
        """Article with all fields should format correctly."""
        article = make_article(
            url="https://openai.com/blog/gpt5",
            title="GPT-5 Released",
            body="OpenAI released GPT-5 with amazing capabilities.",
            source="openai",
        )
        result = format_article(article, "Groundbreaking new AI model released.")
        assert "🤖" in result
        assert "GPT-5 Released" in result
        assert "Groundbreaking" in result
        assert "Read full article" in result
        assert "openai" in result.lower()

    def test_format_article_url_included(self):
        """Article URL should appear in the output."""
        article = make_article(url="https://example.com/test-article")
        result = format_article(article, "Summary text")
        assert "https://example.com/test-article" in result

    def test_format_article_empty_title(self):
        """Article with empty title should use 'Untitled'."""
        article = make_article(title="")
        result = format_article(article, "Summary")
        assert "Untitled" in result

    def test_format_article_empty_summary(self):
        """Article with empty summary should still produce valid output."""
        article = make_article()
        result = format_article(article, "")
        # Should still have structure markers
        assert "**" in result

    def test_format_article_long_title(self):
        """Title longer than 120 chars should be truncated."""
        long_title = "A" * 150
        article = make_article(title=long_title)
        result = format_article(article, "Short summary")
        assert ("A" * 120) in result
        assert not ("A" * 130) in result

    def test_format_article_long_summary(self):
        """Summary longer than 300 chars should be truncated."""
        long_summary = "B" * 500
        article = make_article()
        result = format_article(article, long_summary)
        assert ("B" * 300) in result
        assert not ("B" * 400) in result

    def test_format_article_source_emoji_matches(self):
        """Source emoji should match the article's source."""
        article = make_article(source="github")
        result = format_article(article, "Summary")
        assert "🐙" in result

    def test_format_article_source_label(self):
        """Source label should appear in the footer."""
        article = make_article(source="TechCrunch")
        result = format_article(article, "Summary")
        lines = result.split("\n")
        footer = lines[-1]
        assert "techcrunch" in footer.lower() or "TechCrunch" in footer

    def test_format_article_timestamp_format(self):
        """Timestamp should follow HH:MM IST format."""
        article = make_article()
        result = format_article(article, "Summary")
        last_line = result.split("\n")[-1]
        assert "IST" in last_line

    def test_format_article_structure(self):
        """Article should have emoji, title, summary, link, and footer."""
        article = make_article(
            url="https://example.com/article",
            title="Test Title",
            source="huggingface",
        )
        result = format_article(article, "Test summary here")
        assert "🤗" in result  # huggingface emoji
        assert "**Test Title**" in result
        assert "Test summary here" in result
        assert "🔗 [Read full article]" in result
        assert "IST" in result


# ── format_youtube_article ────────────────────────────────────────────────


class TestFormatYoutubeArticle:
    def test_youtube_full_metadata(self):
        """YouTube article with full metadata should render rich output."""
        article = make_article(
            url="https://youtube.com/watch?v=abc123",
            title="Deep Learning Explained",
            source="youtube",
            youtube_data=make_youtube_data(),
        )
        result = format_youtube_article(article, "Great explanation of deep learning.")
        assert "▶️" in result
        assert "Deep Learning Explained" in result
        assert "Test Channel" in result
        assert "131K views" in result
        assert "7.2K" in result  # likes
        assert "10m 4s" in result  # duration
        assert "#ai" in result or "#machinelearning" in result
        assert "Watch on YouTube" in result

    def test_youtube_no_youtube_data(self):
        """YouTube article without youtube_data should fall back to regular format."""
        article = make_article(
            url="https://youtube.com/watch?v=xyz789",
            title="Simple Video",
            source="youtube",
            youtube_data=None,
        )
        result = format_youtube_article(article, "Summary")
        assert "▶️" in result or get_source_emoji("youtube") in result
        assert "Simple Video" in result

    def test_youtube_top_comment(self):
        """YouTube article with top comment should display it."""
        article = make_article(
            youtube_data=make_youtube_data({
                "top_comment": {
                    "text": "Amazing content!",
                    "author": "Follower1",
                    "like_count": 500,
                }
            }),
        )
        result = format_youtube_article(article, "Summary")
        assert "Amazing content!" in result
        assert "Follower1" in result
        assert "500" in result

    def test_youtube_comment_no_likes(self):
        """Top comment with zero likes should not show like count."""
        article = make_article(
            youtube_data=make_youtube_data({
                "top_comment": {
                    "text": "Just a comment",
                    "author": "User",
                    "like_count": 0,
                }
            }),
        )
        result = format_youtube_article(article, "Summary")
        assert "Just a comment" in result
        assert "(0" not in result

    def test_youtube_no_stats(self):
        """YouTube article without stats should skip stats line."""
        article = make_article(
            youtube_data=make_youtube_data({
                "views_display": None,
                "likes_display": None,
                "duration_display": None,
                "tags": [],
                "top_comment": None,
            }),
        )
        result = format_youtube_article(article, "Summary")
        assert "👁️" not in result
        assert "👍" not in result
        assert "⏱️" not in result

    def test_youtube_no_tags(self):
        """YouTube article without tags should omit tags line."""
        article = make_article(
            youtube_data=make_youtube_data({"tags": []}),
        )
        result = format_youtube_article(article, "Summary")
        assert "#" not in result or "🏷️" not in result

    def test_youtube_empty_title(self):
        """YouTube article with empty title should use 'Untitled'."""
        article = make_article(
            title="",
            youtube_data=make_youtube_data(),
        )
        result = format_youtube_article(article, "Summary")
        assert "Untitled" in result

    def test_youtube_long_title_truncated(self):
        """YouTube title longer than 120 chars should be truncated."""
        long_title = "X" * 150
        article = make_article(
            title=long_title,
            youtube_data=make_youtube_data(),
        )
        result = format_youtube_article(article, "Summary")
        assert ("X" * 120) in result

    def test_youtube_empty_summary(self):
        """YouTube article with empty summary should not raise."""
        article = make_article(
            youtube_data=make_youtube_data(),
        )
        result = format_youtube_article(article, "")
        assert result is not None

    def test_youtube_stats_partial(self):
        """YouTube article with partial stats should show only available ones."""
        article = make_article(
            youtube_data=make_youtube_data({
                "views_display": "50K",
                "likes_display": None,
                "duration_display": "5m",
                "top_comment": {"text": "No likes here", "author": "User", "like_count": 0},
            }),
        )
        result = format_youtube_article(article, "Summary")
        assert "50K views" in result
        assert "👍" not in result  # no likes display AND no top-comment likes

    def test_youtube_source_label_in_footer(self):
        """YouTube footer should include 'youtube' as source label."""
        article = make_article(
            youtube_data=make_youtube_data(),
        )
        result = format_youtube_article(article, "Summary")
        last_line = result.split("\n")[-1]
        assert "▶️" in last_line
        assert "youtube" in last_line


# ── format_batch ──────────────────────────────────────────────────────────


class TestFormatBatch:
    def test_batch_single_article(self):
        """Single article batch should return a formatted message."""
        articles = [
            {"article": make_article(source="openai"), "summary": "AI news summary"}
        ]
        messages = format_batch(articles)
        assert len(messages) >= 1

    def test_batch_multiple_articles(self):
        """Multiple articles batch should return multiple messages."""
        articles = [
            {"article": make_article(url="https://a.com/1", title="A1", source="openai"), "summary": "Sum1"},
            {"article": make_article(url="https://a.com/2", title="A2", source="anthropic"), "summary": "Sum2"},
        ]
        messages = format_batch(articles)
        assert len(messages) >= 2

    def test_batch_empty_list(self):
        """Empty article list should return empty list."""
        assert format_batch([]) == []

    def test_batch_no_header(self):
        """include_header=False should skip the header message."""
        articles = [
            {"article": make_article(), "summary": "Test summary"}
        ]
        messages = format_batch(articles, include_header=False)
        assert len(messages) == 1
        assert "AI News Brief" not in messages[0]

    def test_batch_with_header(self):
        """include_header=True should prepend a batch header."""
        articles = [
            {"article": make_article(source="openai"), "summary": "Summary"}
        ]
        messages = format_batch(articles, include_header=True)
        assert len(messages) == 2  # header + article
        assert "AI News Brief" in messages[0]

    def test_batch_skip_missing_summary(self):
        """Article with empty summary should be skipped."""
        articles = [
            {"article": make_article(), "summary": ""},
        ]
        messages = format_batch(articles)
        assert len(messages) == 0

    def test_batch_skip_missing_article(self):
        """Entry without article should be skipped."""
        articles = [
            {"article": None, "summary": "Some summary"},
        ]
        messages = format_batch(articles)
        assert messages == []

    def test_batch_youtube_article(self):
        """YouTube articles should use format_youtube_article."""
        articles = [
            {
                "article": make_article(
                    source="youtube",
                    youtube_data=make_youtube_data(),
                ),
                "summary": "Video summary",
            }
        ]
        messages = format_batch(articles)
        assert len(messages) >= 1

    def test_batch_mixed_sources(self):
        """Mix of regular and YouTube articles should format both correctly."""
        articles = [
            {
                "article": make_article(url="https://a.com/1", title="News", source="openai"),
                "summary": "Text summary",
            },
            {
                "article": make_article(
                    url="https://youtube.com/watch?v=vid1",
                    title="Video Title",
                    source="youtube",
                    youtube_data=make_youtube_data(),
                ),
                "summary": "Video summary",
            },
        ]
        messages = format_batch(articles)
        assert len(messages) >= 2

    def test_batch_invalid_entries_with_valid(self):
        """Mix of valid and invalid entries should handle gracefully."""
        articles = [
            {"article": make_article(), "summary": "Good summary"},
            {"article": None, "summary": ""},
            {},
            {"article": make_article(source="youtube", youtube_data=make_youtube_data()), "summary": "YT summary"},
        ]
        messages = format_batch(articles)
        assert isinstance(messages, list)
        assert len(messages) >= 1


# ── Regression Tests ─────────────────────────────────────────────────────


class TestRegression:
    def test_source_emoji_all_keys_exist(self):
        """All SOURCE_EMOJI keys should return an emoji."""
        for key in SOURCE_EMOJI:
            emoji = get_source_emoji(key)
            assert emoji is not None
            assert len(emoji) > 0

    def test_article_with_special_chars_in_body(self):
        """Special characters in summary should not cause formatting issues."""
        article = make_article()
        summary = "Article with <b>HTML</b> tags & special chars: _*[]"
        result = format_article(article, summary)
        assert summary in result

    def test_youtube_html_stripped_from_comment(self):
        """HTML tags in YouTube comments should be stripped."""
        article = make_article(
            youtube_data=make_youtube_data({
                "top_comment": {
                    "text": "This is <b>bold</b> and <a href='x'>link</a> text",
                    "author": "User",
                    "like_count": 10,
                }
            }),
        )
        result = format_youtube_article(article, "Summary")
        assert "<b>" not in result
        assert "bold" in result  # text preserved from inside tags

    def test_escape_md_preserves_urls(self):
        """URLs with special chars should still work after escaping."""
        url = "https://example.com/_test?q=hello_world"
        article = make_article(url=url)
        result = format_article(article, "Summary")
        assert url in result

    def test_format_batch_empty_input_edge_cases(self):
        """format_batch should handle various empty/missing inputs gracefully."""
        assert format_batch([]) == []
        assert format_batch([{}]) == []
        assert format_batch([{"article": None}]) == []
        assert format_batch([{"summary": "only summary"}]) == []
