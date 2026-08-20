"""Unit tests for modules/dispatcher.py — AsyncDispatcher core logic.

All external collaborators (db, llm, formatter, sender) are mocked so the tests
exercise the dispatcher's own branching: dedup-on-enqueue, batch short-circuits,
success accounting, and error handling. No network, no API keys, no Telegram.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import AsyncMock, MagicMock

import pytest

import modules.dispatcher as dispatcher


def make_article(title="T", url="https://x.com", url_hash="h1"):
    class A:
        def __init__(self, t, u, h):
            self.title = t
            self.url = u
            self.url_hash = h

    return A(title, url, url_hash)


@pytest.fixture
def mock_deps(monkeypatch):
    db = MagicMock()
    db.is_seen.return_value = False
    llm_mod = MagicMock()
    formatter_mod = MagicMock()
    sender_mod = MagicMock()
    sender_mod.send_batch = AsyncMock(return_value=1)
    monkeypatch.setattr(dispatcher, "db", db)
    monkeypatch.setattr(dispatcher, "llm", llm_mod)
    monkeypatch.setattr(dispatcher, "formatter", formatter_mod)
    monkeypatch.setattr(dispatcher, "sender", sender_mod)
    monkeypatch.setattr("modules.dispatcher.config.LLM_PROVIDER_ORDER", ["groq"])
    return {"db": db, "llm": llm_mod, "formatter": formatter_mod, "sender": sender_mod}


class TestQueueItem:
    def test_defaults(self):
        qi = dispatcher.QueueItem(article=object())
        assert qi.priority == 0
        assert qi.enqueued_at == 0.0


class TestEnqueue:
    @pytest.mark.asyncio
    async def test_enqueue_new(self, mock_deps):
        d = dispatcher.AsyncDispatcher()
        ok = await d.enqueue(make_article())
        assert ok is True
        assert d.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_enqueue_skips_duplicate(self, mock_deps):
        mock_deps["db"].is_seen.return_value = True
        d = dispatcher.AsyncDispatcher()
        ok = await d.enqueue(make_article())
        assert ok is False
        assert d.queue.qsize() == 0


class TestProcessBatch:
    @pytest.mark.asyncio
    async def test_empty_batch(self, mock_deps):
        d = dispatcher.AsyncDispatcher()
        await d._process_batch([])
        mock_deps["llm"].summarise_all_flex.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_summaries_short_circuits(self, mock_deps):
        mock_deps["llm"].summarise_all_flex = AsyncMock(return_value=[])
        d = dispatcher.AsyncDispatcher()
        await d._process_batch([dispatcher.QueueItem(article=make_article())])
        mock_deps["llm"].filter_by_score.assert_not_called()
        mock_deps["sender"].send_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_filtered_out_short_circuits(self, mock_deps):
        mock_deps["llm"].summarise_all_flex = AsyncMock(
            return_value=[{"summary": "s", "score": 9}]
        )
        mock_deps["llm"].filter_by_score.return_value = []
        d = dispatcher.AsyncDispatcher()
        await d._process_batch([dispatcher.QueueItem(article=make_article())])
        mock_deps["formatter"].format_batch.assert_not_called()
        mock_deps["sender"].send_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_format_empty_short_circuits(self, mock_deps):
        mock_deps["llm"].summarise_all_flex = AsyncMock(
            return_value=[{"summary": "s", "score": 9}]
        )
        mock_deps["llm"].filter_by_score.return_value = [{"summary": "s", "score": 9}]
        mock_deps["formatter"].format_batch.return_value = []
        d = dispatcher.AsyncDispatcher()
        await d._process_batch([dispatcher.QueueItem(article=make_article())])
        mock_deps["sender"].send_batch.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_increments_processed_and_logs(self, mock_deps):
        mock_deps["llm"].summarise_all_flex = AsyncMock(
            return_value=[{"summary": "s", "score": 9}]
        )
        mock_deps["llm"].filter_by_score.return_value = [{"summary": "s", "score": 9}]
        mock_deps["formatter"].format_batch.return_value = ["msg"]
        mock_deps["sender"].send_batch = AsyncMock(return_value=1)
        d = dispatcher.AsyncDispatcher()
        art = make_article(title="MyTitle")
        await d._process_batch([dispatcher.QueueItem(article=art)])
        assert d.items_processed == 1
        mock_deps["sender"].send_batch.assert_called_once()
        mock_deps["db"].log_delivery.assert_called_once()

    @pytest.mark.asyncio
    async def test_sender_error_increments_failed(self, mock_deps):
        mock_deps["llm"].summarise_all_flex = AsyncMock(
            return_value=[{"summary": "s", "score": 9}]
        )
        mock_deps["llm"].filter_by_score.return_value = [{"summary": "s", "score": 9}]
        mock_deps["formatter"].format_batch.return_value = ["msg"]
        mock_deps["sender"].send_batch = AsyncMock(side_effect=RuntimeError("boom"))
        d = dispatcher.AsyncDispatcher()
        await d._process_batch([dispatcher.QueueItem(article=make_article())])
        assert d.items_failed == 1
        mock_deps["db"].log_error.assert_called()


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_stats(self, mock_deps):
        d = dispatcher.AsyncDispatcher()
        stats = await d.get_stats()
        assert "queue_size" in stats
        assert stats["processing"] is False

    @pytest.mark.asyncio
    async def test_start_stop(self, mock_deps):
        d = dispatcher.AsyncDispatcher()
        await d.start()
        assert d.processing is True
        await d.stop()
        assert d.processing is False
