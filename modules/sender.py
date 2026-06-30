import asyncio
import logging
from datetime import datetime

import httpx

import config

logger = logging.getLogger(__name__)

# Proxy for Telegram (set TELEGRAM_PROXY in .env if api.telegram.org is blocked)
TELEGRAM_PROXY = getattr(config, "TELEGRAM_PROXY", "") or ""
TELEGRAM_API = getattr(config, "TELEGRAM_API_URL", "") or "https://api.telegram.org"


def _get_http_client() -> httpx.AsyncClient:
    """Create httpx client with optional proxy support."""
    kwargs = {"timeout": 30}
    if TELEGRAM_PROXY:
        kwargs["proxy"] = TELEGRAM_PROXY
        logger.info(f"[Telegram] Using proxy: {TELEGRAM_PROXY}")
    return httpx.AsyncClient(**kwargs)


async def _send_via_http(token: str, chat_id: str, text: str) -> bool:
    """Send message via direct HTTP POST to Telegram Bot API.

    Bypasses python-telegram-bot library — works with proxy support.
    """
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    async with _get_http_client() as client:
        resp = await client.post(url, json=payload)

        if resp.status_code == 200:
            return True
        elif resp.status_code == 429:
            data = resp.json()
            retry_after = data.get("parameters", {}).get("retry_after", 30)
            print(f"[Telegram] Flood wait {retry_after}s")
            await asyncio.sleep(retry_after)
            # Retry once
            async with _get_http_client() as retry_client:
                resp2 = await retry_client.post(url, json=payload)
                return resp2.status_code == 200
        else:
            logger.error(f"[Telegram] HTTP {resp.status_code}: {resp.text[:200]}")
            return False


async def send_message(token: str, chat_id: str, text: str, max_retries: int = 3) -> bool:
    """Send a single message with retry on connection errors."""
    for attempt in range(max_retries):
        try:
            return await _send_via_http(token, chat_id, text)
        except Exception as e:
            error_str = str(e)
            is_connect_error = (
                "ConnectError" in type(e).__name__
                or "connect" in error_str.lower()
                or "timeout" in error_str.lower()
            )

            if is_connect_error and attempt < max_retries - 1:
                wait = 5 * (2 ** attempt)
                logger.warning(
                    f"[Telegram] Connection error (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait}s: {error_str[:100]}"
                )
                await asyncio.sleep(wait)
                continue

            logger.error(f"[Telegram] Send failed: {e}")
            return False

    logger.error(f"[Telegram] All {max_retries} attempts failed")
    return False


async def send_batch(messages: list[str], chat_id: str = None) -> int:
    if not messages:
        return 0

    target_chat_id = chat_id or config.TELEGRAM_CHAT_ID

    if not config.TELEGRAM_BOT_TOKEN or not target_chat_id:
        logger.error("[Telegram] Bot token or chat ID not configured")
        return 0

    sent_count = 0
    for i, message in enumerate(messages):
        success = await send_message(
            config.TELEGRAM_BOT_TOKEN, target_chat_id, message
        )

        if success:
            sent_count += 1
            print(
                f"[Telegram] Sent {i + 1}/{len(messages)}: {message.split(chr(10))[0][:50]}..."
            )
        else:
            logger.warning(f"[Telegram] Failed to send message {i + 1}")

        if i < len(messages) - 1:
            await asyncio.sleep(3)

    return sent_count


async def send_error_alert(error_message: str, admin_chat_id: str | None = None):
    if not admin_chat_id or not config.TELEGRAM_BOT_TOKEN:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    message = f"⚠️ AI News Bot Error\n\n{error_message}\n\n⏰ {timestamp}"

    await send_message(config.TELEGRAM_BOT_TOKEN, admin_chat_id, message)

