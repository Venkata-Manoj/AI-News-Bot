"""Unit tests for modules/youtube_fetcher.py — pure helper functions.

Covers ISO duration parsing, duration/count formatting, VTT timestamp parsing,
VTT transcript parsing (with deduplication), transcript chunking, and the
uploads-playlist ID conversion. No network, no API key required.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import modules.youtube_fetcher as yt


class TestIsoDuration:
    def test_none(self):
        assert yt.parse_iso_duration(None) == 0  # type: ignore[arg-type]

    def test_empty(self):
        assert yt.parse_iso_duration("") == 0

    def test_full(self):
        assert yt.parse_iso_duration("PT1H2M3S") == 3723

    def test_minutes_seconds(self):
        assert yt.parse_iso_duration("PT5M30S") == 330

    def test_seconds_only(self):
        assert yt.parse_iso_duration("PT45S") == 45

    def test_invalid(self):
        assert yt.parse_iso_duration("notiso") == 0


class TestFormatDuration:
    def test_zero(self):
        assert yt.format_duration(0) == "0s"

    def test_seconds(self):
        assert yt.format_duration(45) == "45s"

    def test_minutes(self):
        assert yt.format_duration(125) == "2m 5s"

    def test_hours(self):
        assert yt.format_duration(3723) == "1h 2m"


class TestFormatCount:
    def test_small(self):
        assert yt.format_count(999) == "999"

    def test_thousands(self):
        assert yt.format_count(1234) == "1.2K"

    def test_millions(self):
        assert yt.format_count(2_500_000) == "2.5M"


class TestVttTimestamp:
    def test_three_parts(self):
        assert yt.parse_vtt_timestamp("01:02:03.456") == 3723.456

    def test_two_parts(self):
        assert yt.parse_vtt_timestamp("02:03.456") == 123.456

    def test_invalid(self):
        assert yt.parse_vtt_timestamp("garbage") == 0.0


class TestParseVtt:
    def test_empty(self):
        assert yt.parse_vtt("") == {"segments": [], "fullText": ""}

    def test_parses_segments(self):
        content = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:03.000\n"
            "Hello world\n\n"
            "00:00:03.500 --> 00:00:05.000\n"
            "Second line\n"
        )
        res = yt.parse_vtt(content)
        assert len(res["segments"]) == 2
        assert res["fullText"] == "Hello world Second line"

    def test_dedup(self):
        content = (
            "WEBVTT\n\n"
            "00:00:01.000 --> 00:00:03.000\n"
            "Repeat\n\n"
            "00:00:03.500 --> 00:00:05.000\n"
            "Repeat\n"
        )
        res = yt.parse_vtt(content)
        assert len(res["segments"]) == 1


class TestChunkTranscript:
    def test_empty(self):
        assert yt.chunk_transcript([], "vid", "title") == []

    def test_single_chunk(self):
        segs = [{"text": "one two three", "start": 0.0, "end": 1.0}]
        chunks = yt.chunk_transcript(segs, "v1", "T")
        assert len(chunks) == 1
        assert chunks[0]["text"] == "one two three"
        assert chunks[0]["video_url"].endswith("v1")
        assert chunks[0]["chunk_index"] == 0


class TestUploadsPlaylist:
    def test_convert(self):
        assert yt.get_uploads_playlist_id("UC123") == "UU123"

    def test_no_uc_prefix_passthrough(self):
        assert yt.get_uploads_playlist_id("UU123") == "UU123"
