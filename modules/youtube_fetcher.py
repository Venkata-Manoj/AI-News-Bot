"""YouTube channel scraping module.

Implements a 4-stage pipeline:
1. Fetch all videos from configured channels via YouTube Data API v3
2. Download & parse transcripts via yt-dlp CLI
3. Chunk transcripts for search/embeddings
4. Fetch top comments per video

Integrates with the existing Article-based pipeline.
"""

import asyncio
import json
import logging
import os
import re
import shutil
from datetime import datetime

import aiohttp

import config

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
VTT_DIR = os.path.join(config.DATA_DIR, "vtt")


# ============================================================
# Utilities
# ============================================================

def parse_iso_duration(iso: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    if not iso:
        return 0
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def format_duration(seconds: int) -> str:
    """Format seconds to human readable (e.g., '1h 2m')."""
    if seconds <= 0:
        return "0s"
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def format_count(n: int) -> str:
    """Format large numbers (1234 → '1.2K')."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def parse_vtt_timestamp(ts: str) -> float:
    """Parse VTT timestamp '00:01:23.456' to seconds."""
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return 0.0


# ============================================================
# Stage 1: Fetch Videos from Channel
# ============================================================

async def get_channel_id(
    handle: str, api_key: str, session: aiohttp.ClientSession
) -> str | None:
    """Resolve @handle to UC... channel ID."""
    handle = handle.strip()
    if not handle.startswith("@"):
        handle = f"@{handle}"

    url = f"{YOUTUBE_API_BASE}/channels"
    params = {"part": "id", "forHandle": handle, "key": api_key}

    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status != 200:
                logger.warning(f"[YouTube] Channel lookup failed for {handle}: HTTP {resp.status}")
                return None
            data = await resp.json()
            items = data.get("items", [])
            if items:
                cid = items[0]["id"]
                logger.info(f"[YouTube] Resolved {handle} → {cid}")
                return cid
            logger.warning(f"[YouTube] No channel found for handle: {handle}")
            return None
    except Exception as e:
        logger.error(f"[YouTube] Error resolving {handle}: {e}")
        return None


def get_uploads_playlist_id(channel_id: str) -> str:
    """Convert UC... channel ID to UU... uploads playlist ID."""
    if channel_id.startswith("UC"):
        return "UU" + channel_id[2:]
    return channel_id


async def fetch_video_ids(
    playlist_id: str,
    api_key: str,
    session: aiohttp.ClientSession,
    max_videos: int = 50,
) -> list[str]:
    """Paginate through uploads playlist to get video IDs."""
    video_ids = []
    page_token = None

    while len(video_ids) < max_videos:
        url = f"{YOUTUBE_API_BASE}/playlistItems"
        params = {
            "part": "snippet",
            "maxResults": min(50, max_videos - len(video_ids)),
            "playlistId": playlist_id,
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            async with session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"[YouTube] Playlist fetch failed: HTTP {resp.status}")
                    break
                data = await resp.json()
                for item in data.get("items", []):
                    vid = item.get("snippet", {}).get("resourceId", {}).get("videoId")
                    if vid:
                        video_ids.append(vid)
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            logger.error(f"[YouTube] Error fetching playlist {playlist_id}: {e}")
            break

    return video_ids[:max_videos]


async def fetch_video_details(
    video_ids: list[str], api_key: str, session: aiohttp.ClientSession
) -> list[dict]:
    """Batch fetch video details (50 per API call)."""
    all_details = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        url = f"{YOUTUBE_API_BASE}/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(batch),
            "key": api_key,
        }

        try:
            async with session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"[YouTube] Video details failed: HTTP {resp.status}")
                    continue
                data = await resp.json()

                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    stats = item.get("statistics", {})
                    content = item.get("contentDetails", {})
                    duration_raw = content.get("duration", "PT0S")

                    detail = {
                        "video_id": item["id"],
                        "title": snippet.get("title", "Untitled"),
                        "description": snippet.get("description", ""),
                        "thumbnail": (
                            snippet.get("thumbnails", {}).get("maxres", {}).get("url")
                            or snippet.get("thumbnails", {}).get("high", {}).get("url")
                            or snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
                        ),
                        "published_at": snippet.get("publishedAt", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "tags": snippet.get("tags", []),
                        "duration_raw": duration_raw,
                        "duration_seconds": parse_iso_duration(duration_raw),
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                    }
                    all_details.append(detail)
        except Exception as e:
            logger.error(f"[YouTube] Error fetching video details: {e}")

        # Small delay between batches
        if i + 50 < len(video_ids):
            await asyncio.sleep(0.5)

    return all_details


# ============================================================
# Stage 2: Download & Parse Transcripts
# ============================================================

async def download_transcript(
    video_id: str, lang: str = "en", output_dir: str = None
) -> str | None:
    """Download VTT subtitle via yt-dlp, return file content or None."""
    if output_dir is None:
        output_dir = VTT_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Check if already downloaded (cache hit)
    for suffix in [f".{lang}.vtt", f".{lang}-orig.vtt"]:
        existing = os.path.join(output_dir, f"{video_id}{suffix}")
        if os.path.exists(existing):
            logger.info(f"[YouTube] VTT cache hit: {video_id}")
            with open(existing, encoding="utf-8") as f:
                return f.read()

    # Check if yt-dlp is available (system PATH or venv Scripts)
    ytdlp_bin = shutil.which("yt-dlp")
    if not ytdlp_bin:
        # Fallback: check venv Scripts directory
        venv_bin = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "Scripts", "yt-dlp.exe")
        if os.path.exists(venv_bin):
            ytdlp_bin = venv_bin
        else:
            # Also try Linux/Mac venv path
            venv_bin_unix = os.path.join(os.path.dirname(os.path.dirname(__file__)), "venv", "bin", "yt-dlp")
            if os.path.exists(venv_bin_unix):
                ytdlp_bin = venv_bin_unix
            else:
                logger.warning("[YouTube] yt-dlp not found in PATH or venv, skipping transcripts")
                return None

    video_url = f"https://youtube.com/watch?v={video_id}"
    output_template = os.path.join(output_dir, "%(id)s")

    cmd = [
        ytdlp_bin,
        "--write-auto-subs",
        "--sub-lang", lang,
        "--skip-download",
        "-o", output_template,
        video_url,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=60
            )
        except TimeoutError:
            process.kill()
            await process.communicate()
            logger.warning(f"[YouTube] yt-dlp timed out for {video_id}")
            return None

        # Find the downloaded VTT file
        for suffix in [f".{lang}.vtt", f".{lang}-orig.vtt"]:
            vtt_path = os.path.join(output_dir, f"{video_id}{suffix}")
            if os.path.exists(vtt_path):
                with open(vtt_path, encoding="utf-8") as f:
                    content = f.read()
                logger.info(f"[YouTube] Downloaded transcript for {video_id}")
                return content

        logger.info(f"[YouTube] No subtitles available for {video_id}")
        return None

    except Exception as e:
        logger.error(f"[YouTube] Transcript error for {video_id}: {e}")
        return None


def parse_vtt(file_content: str) -> dict:
    """Parse VTT content into segments with deduplication."""
    if not file_content:
        return {"segments": [], "fullText": ""}

    lines = file_content.split("\n")
    segments = []
    seen = set()
    current_start = None
    current_end = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("WEBVTT") or stripped == "" or re.match(r"^\d+$", stripped):
            continue

        # Lines with positioning metadata
        if "align:" in line or "position:" in line:
            time_match = re.search(
                r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})", line
            )
            if time_match:
                current_start = parse_vtt_timestamp(time_match.group(1))
                current_end = parse_vtt_timestamp(time_match.group(2))
            continue

        # Timestamp line
        time_match = re.search(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})", line
        )
        if time_match:
            current_start = parse_vtt_timestamp(time_match.group(1))
            current_end = parse_vtt_timestamp(time_match.group(2))
            continue

        # Text line — clean HTML tags and deduplicate
        text = re.sub(r"<[^>]+>", "", line).strip()
        if text and text not in seen and current_start is not None:
            seen.add(text)
            segments.append({"start": current_start, "end": current_end, "text": text})

    full_text = " ".join(s["text"] for s in segments)
    return {"segments": segments, "fullText": full_text}


# ============================================================
# Stage 3: Chunk Transcripts
# ============================================================

def chunk_transcript(segments: list[dict], video_id: str, title: str) -> list[dict]:
    """Split transcript into 500-word overlapping chunks."""
    if not segments:
        return []

    words = []
    for seg in segments:
        for word in seg["text"].split():
            words.append({"word": word, "start": seg["start"], "end": seg["end"]})

    if not words:
        return []

    TARGET, OVERLAP = 500, 75
    STRIDE = TARGET - OVERLAP
    chunks = []
    i = 0

    while i < len(words):
        word_slice = words[i : i + TARGET]
        text = " ".join(w["word"] for w in word_slice)

        chunks.append({
            "id": f"{video_id}_chunk_{len(chunks)}",
            "text": text,
            "title": title,
            "video_url": f"https://youtube.com/watch?v={video_id}",
            "timestamp_url": f"https://youtube.com/watch?v={video_id}&t={int(word_slice[0]['start'])}s",
            "start_time": word_slice[0]["start"],
            "end_time": word_slice[-1]["end"],
            "chunk_index": len(chunks),
        })
        i += STRIDE

    # Absorb tiny final chunk into previous
    if len(chunks) > 1:
        last = chunks[-1]
        if len(last["text"].split()) < OVERLAP:
            prev = chunks[-2]
            prev["text"] += " " + last["text"]
            prev["end_time"] = last["end_time"]
            chunks.pop()

    return chunks


# ============================================================
# Stage 4: Fetch Comments
# ============================================================

async def fetch_comments(
    video_id: str, api_key: str, session: aiohttp.ClientSession, max_results: int = 5
) -> list[dict]:
    """Fetch top comments for a video. Returns [] on 403 (disabled)."""
    url = f"{YOUTUBE_API_BASE}/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "order": "relevance",
        "key": api_key,
    }

    try:
        async with session.get(
            url, params=params, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 403:
                return []  # comments disabled — totally normal
            if resp.status != 200:
                logger.warning(f"[YouTube] Comments API failed for {video_id}: HTTP {resp.status}")
                return []

            data = await resp.json()
            comments = []
            for item in data.get("items", []):
                top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                comments.append({
                    "comment_id": item.get("id", ""),
                    "video_id": video_id,
                    "author": top.get("authorDisplayName", ""),
                    "text": top.get("textDisplay", ""),
                    "like_count": top.get("likeCount", 0),
                    "published_at": top.get("publishedAt", ""),
                })

            return comments
    except Exception as e:
        logger.warning(f"[YouTube] Comments failed for {video_id}: {e}")
        return []


# ============================================================
# Orchestrator: Full Pipeline
# ============================================================

async def fetch_channel_videos(
    handle: str,
    api_key: str,
    session: aiohttp.ClientSession,
    max_videos: int = None,
    fetch_transcripts: bool = True,
    fetch_video_comments: bool = True,
) -> list:
    """Full pipeline for one channel → returns list of Article objects."""
    from modules.db import db
    from modules.fetcher import Article

    if max_videos is None:
        max_videos = getattr(config, "YOUTUBE_MAX_VIDEOS_PER_CHANNEL", 10)

    # Stage 1a: Resolve channel
    channel_id = await get_channel_id(handle, api_key, session)
    if not channel_id:
        return []

    # Stage 1b: Get video IDs from uploads playlist
    playlist_id = get_uploads_playlist_id(channel_id)
    video_ids = await fetch_video_ids(playlist_id, api_key, session, max_videos)
    if not video_ids:
        logger.info(f"[YouTube] No videos found for {handle}")
        return []

    logger.info(f"[YouTube] Found {len(video_ids)} videos for {handle}")

    # Stage 1c: Enrich with full details
    details = await fetch_video_details(video_ids, api_key, session)

    # Delta check — filter to only new videos for transcript download
    new_details = []
    for d in details:
        if not db.is_youtube_video_seen(d["video_id"]):
            new_details.append(d)
        else:
            # Always refresh stats even for seen videos
            db.update_youtube_video_stats(
                d["video_id"], d["views"], d["likes"], d["comment_count"]
            )

    logger.info(f"[YouTube] {len(new_details)} new videos (of {len(details)} total) for {handle}")

    articles = []
    for video in new_details:
        vid = video["video_id"]

        # Stage 2: Download & parse transcript
        transcript_text = ""
        chunks = []
        if fetch_transcripts:
            vtt_content = await download_transcript(
                vid, lang=getattr(config, "YOUTUBE_TRANSCRIPT_LANG", "en")
            )
            if vtt_content:
                parsed = parse_vtt(vtt_content)
                transcript_text = parsed["fullText"]
                chunks = chunk_transcript(parsed["segments"], vid, video["title"])
            # Small delay between yt-dlp calls
            await asyncio.sleep(1)

        # Stage 4: Fetch comments
        comments = []
        if fetch_video_comments and getattr(config, "YOUTUBE_FETCH_COMMENTS", True):
            comments = await fetch_comments(vid, api_key, session, max_results=3)

        # Persist to YouTube tables
        db.upsert_youtube_video({
            "video_id": vid,
            "channel_id": channel_id,
            "title": video["title"],
            "description": video["description"][:2000],
            "thumbnail": video["thumbnail"],
            "published_at": video["published_at"],
            "duration_seconds": video["duration_seconds"],
            "tags": json.dumps(video["tags"][:10]),
            "views": video["views"],
            "likes": video["likes"],
            "comment_count": video["comment_count"],
            "transcript": transcript_text[:5000],
        })

        if comments:
            db.insert_youtube_comments(comments)

        # Build Article body: prefer transcript snippet, fallback to description
        body = transcript_text[:400] if transcript_text else video["description"][:400]

        # Build Article with youtube_data extension
        article = Article(
            title=video["title"],
            url=f"https://youtube.com/watch?v={vid}",
            body=body,
            source="youtube",
            published=datetime.fromisoformat(
                video["published_at"].replace("Z", "+00:00")
            ) if video["published_at"] else datetime.utcnow(),
        )

        # Attach YouTube-specific metadata for the formatter
        article.youtube_data = {
            "video_id": vid,
            "channel_title": video["channel_title"],
            "thumbnail": video["thumbnail"],
            "duration_seconds": video["duration_seconds"],
            "duration_display": format_duration(video["duration_seconds"]),
            "views": video["views"],
            "views_display": format_count(video["views"]),
            "likes": video["likes"],
            "likes_display": format_count(video["likes"]),
            "tags": video["tags"][:5],
            "top_comment": comments[0] if comments else None,
            "chunks": chunks,
            "has_transcript": bool(transcript_text),
        }

        articles.append(article)

    logger.info(f"[YouTube] Produced {len(articles)} articles from {handle}")
    return articles


async def fetch_all_channels(channels: list[str], api_key: str) -> list:
    """Fetch all configured YouTube channels."""
    if not api_key:
        logger.warning("[YouTube] No YOUTUBE_API_KEY set, skipping YouTube source")
        return []

    if not channels:
        logger.info("[YouTube] No channels configured")
        return []

    all_articles = []
    async with aiohttp.ClientSession() as session:
        for handle in channels:
            handle = handle.strip()
            if not handle:
                continue
            try:
                articles = await fetch_channel_videos(handle, api_key, session)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"[YouTube] Error processing channel {handle}: {e}")
            # Small delay between channels
            await asyncio.sleep(0.5)

    print(f"[YouTube] Total: {len(all_articles)} new videos from {len(channels)} channels")
    return all_articles
