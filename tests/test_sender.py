"""Unit tests for modules/sender.py — Telegram message delivery.

Tests HTTP retry logic, flood wait handling, error alerts, and batch sending.
Uses mocked httpx — no network access required.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_config():
    """Mock config module to avoid requiring .env file."""
    with patch("modules.sender.config") as mock_cfg:
        mock_cfg.TELEGRAM_BOT_TOKEN = "test:token"
        mock_cfg.TELEGRAM_CHAT_ID = "123456"
        mock_cfg.TELEGRAM_PROXY = ""
        mock_cfg.TELEGRAM_API_URL = "https://api.telegram.org"
        yield mock_cfg


@pytest.fixture
def mock_http_client():
    """Create a mock httpx.AsyncClient for controlled responses."""
    client = AsyncMock(spec_set=["post", "__aenter__", "__aexit__"])
    # Make it work as async context manager
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


# ── send_message tests ─────────────────────────────────────────────────────


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_config):
        """Successful 200 response should return True."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            from modules.sender import send_message

            result = await send_message("test:token", "123456", "Hello world")
            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_http_500(self, mock_config):
        """HTTP 500 should return False (no retry for server errors)."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.post.return_value = mock_response

            from modules.sender import send_message

            result = await send_message("test:token", "123456", "Hello")
            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_429_retry(self, mock_config):
        """HTTP 429 (flood wait) should retry after waiting."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # First call returns 429, second returns 200
            resp_429 = MagicMock()
            resp_429.status_code = 429
            resp_429.json.return_value = {"parameters": {"retry_after": 1}}

            resp_200 = MagicMock()
            resp_200.status_code = 200

            mock_client.post.side_effect = [resp_429, resp_200]

            with patch("modules.sender.asyncio.sleep", AsyncMock()) as mock_sleep:
                from modules.sender import send_message

                result = await send_message("test:token", "123456", "Hello")
                assert result is True
                assert mock_client.post.call_count == 2
                mock_sleep.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_send_message_connect_error_retry(self, mock_config):
        """Connection errors should retry with backoff."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            import httpx

            # Fail twice then succeed
            connect_error = httpx.ConnectError("connection refused")
            mock_client.post.side_effect = [connect_error, connect_error, MagicMock(status_code=200)]

            with patch("modules.sender.asyncio.sleep", AsyncMock()) as mock_sleep:
                from modules.sender import send_message

                result = await send_message("test:token", "123456", "Hello", max_retries=3)
                assert result is True
                assert mock_client.post.call_count == 3
                # Backoff: 5^1=5s, 5^2=10s (total 2 sleep calls since 3rd attempt succeeds)
                assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_all_retries_fail(self, mock_config):
        """When all retries fail, should return False."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            import httpx

            connect_error = httpx.ConnectError("persistent failure")
            mock_client.post.side_effect = [connect_error, connect_error, connect_error]

            with patch("modules.sender.asyncio.sleep", AsyncMock()):
                from modules.sender import send_message

                result = await send_message("test:token", "123456", "Hello", max_retries=3)
                assert result is False
                assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_send_message_timeout_error(self, mock_config):
        """Timeout errors should be treated as connection errors and retried."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            import httpx

            # The string must contain "timeout" to match sender.py's check
            timeout_error = httpx.TimeoutException("request timeout")
            mock_client.post.side_effect = [timeout_error, MagicMock(status_code=200)]

            with patch("modules.sender.asyncio.sleep", AsyncMock()):
                from modules.sender import send_message

                result = await send_message("test:token", "123456", "Hello", max_retries=3)
                assert result is True
                assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_non_connect_error(self, mock_config):
        """Non-connection errors (e.g., ValueError) should not be retried."""
        with patch("modules.sender.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_client.post.side_effect = ValueError("some other error")

            from modules.sender import send_message

            result = await send_message("test:token", "123456", "Hello", max_retries=3)
            assert result is False
            assert mock_client.post.call_count == 1  # No retry


# ── send_batch tests ───────────────────────────────────────────────────────


class TestSendBatch:
    @pytest.mark.asyncio
    async def test_send_batch_empty(self, mock_config):
        """Empty message list should return 0."""
        from modules.sender import send_batch

        result = await send_batch([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_batch_multiple(self, mock_config):
        """Multiple messages should all be sent."""
        with (
            patch("modules.sender.send_message", AsyncMock(return_value=True)) as mock_send,
            patch("modules.sender.asyncio.sleep", AsyncMock()),
        ):
            from modules.sender import send_batch

            result = await send_batch(["Message 1", "Message 2", "Message 3"])
            assert result == 3
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_send_batch_partial_failure(self, mock_config):
        """When some sends fail, only successful ones should count."""
        with (
            patch("modules.sender.send_message", AsyncMock(side_effect=[True, False, True])) as mock_send,
            patch("modules.sender.asyncio.sleep", AsyncMock()),
        ):
            from modules.sender import send_batch

            result = await send_batch(["Msg 1", "Msg 2", "Msg 3"])
            assert result == 2
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_send_batch_custom_chat_id(self, mock_config):
        """Custom chat_id should be passed to send_message."""
        with patch("modules.sender.send_message", AsyncMock(return_value=True)) as mock_send:
            from modules.sender import send_batch

            await send_batch(["Test"], chat_id="999999")
            mock_send.assert_called_once_with("test:token", "999999", "Test")

    @pytest.mark.asyncio
    async def test_send_batch_no_token(self, mock_config):
        """When no token is configured, should return 0."""
        mock_config.TELEGRAM_BOT_TOKEN = ""
        from modules.sender import send_batch

        result = await send_batch(["Message"])
        assert result == 0

    @pytest.mark.asyncio
    async def test_send_batch_no_chat_id(self, mock_config):
        """When no chat_id is configured, should return 0."""
        mock_config.TELEGRAM_CHAT_ID = ""
        from modules.sender import send_batch

        result = await send_batch(["Message"])
        assert result == 0


# ── send_error_alert tests ─────────────────────────────────────────────────


class TestSendErrorAlert:
    @pytest.mark.asyncio
    async def test_send_error_alert(self, mock_config):
        """Error alert should call send_message with formatted message."""
        with patch("modules.sender.send_message", AsyncMock(return_value=True)) as mock_send:
            from modules.sender import send_error_alert

            await send_error_alert("Something went wrong", admin_chat_id="admin123")
            mock_send.assert_called_once()
            args, _ = mock_send.call_args
            assert "Something went wrong" in args[2]  # Check message content
            assert args[0] == "test:token"
            assert args[1] == "admin123"

    @pytest.mark.asyncio
    async def test_send_error_alert_no_admin(self, mock_config):
        """No admin_chat_id should skip sending."""
        with patch("modules.sender.send_message", AsyncMock()) as mock_send:
            from modules.sender import send_error_alert

            await send_error_alert("Error", admin_chat_id=None)
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_error_alert_no_token(self, mock_config):
        """No bot token should skip sending."""
        mock_config.TELEGRAM_BOT_TOKEN = ""
        with patch("modules.sender.send_message", AsyncMock()) as mock_send:
            from modules.sender import send_error_alert

            await send_error_alert("Error", admin_chat_id="admin123")
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_error_alert_empty_admin(self, mock_config):
        """Empty string admin_chat_id should skip sending (treated as falsy)."""
        with patch("modules.sender.send_message", AsyncMock()) as mock_send:
            from modules.sender import send_error_alert

            await send_error_alert("Error", admin_chat_id="")
            mock_send.assert_not_called()
