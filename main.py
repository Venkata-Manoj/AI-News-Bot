import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    RSS_FEEDS,
    FETCH_OPTIONS,
    FETCH_INTERVAL_MINUTES,
    MAX_ARTICLES_PER_RUN,
    LLM_PROVIDER_ORDER,
    LOG_FILE,
)
from modules import fetcher, dedup, llm, formatter, sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def log_run(
    start_time: datetime,
    articles_fetched: int,
    summaries_count: int,
    sent_count: int,
    llm_calls: int,
):
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        f"[Run] {articles_fetched} fetched, {summaries_count} summarised, {sent_count} sent, {llm_calls} LLM calls, {duration:.1f}s"
    )


async def run_pipeline():
    start_time = datetime.utcnow()
    logger.info(f"[Pipeline] Starting at {start_time.isoformat()}")

    try:
        all_articles = await fetcher.fetch_all(FETCH_OPTIONS)

        if not all_articles:
            logger.info("[Pipeline] No articles fetched")
            return

        new_articles = dedup.filter_new(all_articles)

        if not new_articles:
            logger.info("[Pipeline] No new articles")
            return

        new_articles = dedup.filter_by_keywords(new_articles)

        if not new_articles:
            logger.info("[Pipeline] No AI-relevant articles")
            return

        new_articles = new_articles[:MAX_ARTICLES_PER_RUN]

        for article in new_articles:
            dedup.mark_seen(article.url_hash)

        summaries = await llm.summarise_all_flex(new_articles, LLM_PROVIDER_ORDER)

        if not summaries:
            logger.warning("[Pipeline] No summaries generated")
            return

        high_score = llm.filter_by_score(summaries)

        if not high_score:
            logger.info("[Pipeline] No articles passed relevance threshold")
            return

        messages = formatter.format_batch(high_score)

        if not messages:
            logger.warning("[Pipeline] No messages formatted")
            return

        sent_count = await sender.send_batch(messages)

        llm_calls = llm.get_daily_call_count()

        log_run(start_time, len(new_articles), len(summaries), sent_count, llm_calls)

        logger.info(f"[Pipeline] Complete. Sent {sent_count} messages.")

    except Exception as e:
        logger.error(f"[Pipeline] Error: {e}", exc_info=True)
    except asyncio.CancelledError:
        logger.info("[Pipeline] Cancelled, shutting down...")


def setup_scheduler():
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_pipeline,
        "interval",
        minutes=FETCH_INTERVAL_MINUTES,
        id="ai_news_pipeline",
        next_run_time=datetime.utcnow(),
    )

    scheduler.start()
    logger.info(f"[Scheduler] Started, running every {FETCH_INTERVAL_MINUTES} minutes")

    return scheduler


async def main():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.LOG_DIR, exist_ok=True)

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not set in .env")
        sys.exit(1)

    # Initialize LLM providers
    llm.init_providers()
    provider = llm.get_provider(LLM_PROVIDER_ORDER)

    if not provider:
        logger.error(
            "No LLM provider available. Set at least one API key: GEMINI_API_KEY, NVIDIA_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, or configure Ollama/LMStudio"
        )
        sys.exit(1)

    logger.info(f"[LLM] Using provider: {provider}")

    logger.info("[Main] AI News Bot starting...")

    scheduler = setup_scheduler()

    await run_pipeline()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("[Main] Shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
