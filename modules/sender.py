import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from telegram import Bot
from telegram.error import TelegramError

import config


logger = logging.getLogger(__name__)


async def send_message(bot: Bot, chat_id: str, text: str) -> bool:
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True,
        )
        return True
    except TelegramError as e:
        if "retry_after" in str(e):
            retry_after = int(e.retry_after) if hasattr(e, "retry_after") else 30
            print(f"[Telegram] Flood wait {retry_after}s")
            await asyncio.sleep(retry_after)
            return await send_message(bot, chat_id, text)

        logger.error(f"[Telegram] Send error: {e}")
        return False
    except Exception as e:
        logger.error(f"[Telegram] Unexpected error: {e}")
        return False


async def send_batch(messages: List[str], chat_id: str = None) -> int:
    if not messages:
        return 0

    target_chat_id = chat_id or config.TELEGRAM_CHAT_ID

    if not config.TELEGRAM_BOT_TOKEN or not target_chat_id:
        logger.error("[Telegram] Bot token or chat ID not configured")
        return 0

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)

    sent_count = 0
    for i, message in enumerate(messages):
        success = await send_message(bot, target_chat_id, message)

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


async def send_error_alert(error_message: str, admin_chat_id: Optional[str] = None):
    if not admin_chat_id or not config.TELEGRAM_BOT_TOKEN:
        return

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    message = f"⚠️ AI News Bot Error\n\n{error_message}\n\n⏰ {timestamp}"

    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=message,
        )
    except Exception as e:
        logger.error(f"[Telegram] Alert error: {e}")
