"""Test YouTube fetcher — fetches 1 video from 1 channel (minimal quota usage)."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import aiohttp

import config
from modules.youtube_fetcher import (
    chunk_transcript,
    download_transcript,
    fetch_comments,
    fetch_video_details,
    fetch_video_ids,
    format_count,
    format_duration,
    get_channel_id,
    get_uploads_playlist_id,
    parse_vtt,
)


async def test_youtube():
    api_key = config.YOUTUBE_API_KEY
    if not api_key or api_key == "YOUR_YOUTUBE_API_KEY_HERE":
        print("=" * 60)
        print("YOUTUBE TEST: SKIPPED (no API key set in .env)")
        print("=" * 60)
        return True

    test_handle = "TwoMinutePapers"

    print("=" * 60)
    print("TEST: YouTube Fetcher (1 video, 1 channel)")
    print(f"Channel: @{test_handle}")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # Stage 1: Channel → Video
        print("\n[Stage 1] Resolving channel & fetching 1 video...")
        channel_id = await get_channel_id(test_handle, api_key, session)
        if not channel_id:
            print("FAILED: Could not resolve channel")
            return False
        print(f"  Channel ID: {channel_id}")

        playlist_id = get_uploads_playlist_id(channel_id)
        video_ids = await fetch_video_ids(playlist_id, api_key, session, max_videos=1)
        if not video_ids:
            print("FAILED: No videos found")
            return False

        details = await fetch_video_details(video_ids, api_key, session)
        if not details:
            print("FAILED: No details returned")
            return False

        v = details[0]
        print(f"  Title:    {v['title'][:70]}")
        print(f"  Views:    {format_count(v['views'])}")
        print(f"  Likes:    {format_count(v['likes'])}")
        print(f"  Duration: {format_duration(v['duration_seconds'])}")

        # Stage 2: Transcript
        print("\n[Stage 2] Downloading transcript...")
        vtt = await download_transcript(video_ids[0])
        if vtt:
            parsed = parse_vtt(vtt)
            print(f"  Segments:  {len(parsed['segments'])}")
            print(f"  Text:      {len(parsed['fullText'])} chars")
            print(f"  Preview:   {parsed['fullText'][:100]}...")
        else:
            parsed = {"segments": [], "fullText": ""}
            print("  No subtitles (graceful fallback)")

        # Stage 3: Chunking
        if parsed["segments"]:
            print("\n[Stage 3] Chunking transcript...")
            chunks = chunk_transcript(parsed["segments"], video_ids[0], v["title"])
            print(f"  Chunks: {len(chunks)}")
            if chunks:
                print(f"  Chunk 0: {len(chunks[0]['text'].split())} words")
        else:
            print("\n[Stage 3] Skipped (no transcript)")

        # Stage 4: Comments
        print("\n[Stage 4] Fetching comments...")
        comments = await fetch_comments(video_ids[0], api_key, session, max_results=2)
        print(f"  Comments: {len(comments)}")
        for c in comments[:2]:
            print(f"  - @{c['author'][:20]}: \"{c['text'][:60]}...\" ({c['like_count']} likes)")

    print(f"\n{'=' * 60}")
    print("YOUTUBE TEST: PASSED (all stages OK)")
    print(f"{'=' * 60}")
    return True


if __name__ == "__main__":
    asyncio.run(test_youtube())
