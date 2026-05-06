"""Main entry point for AI News Bot.

Implements production-grade scheduling with Apify integration,
guaranteed low-latency delivery, and automatic recovery.
"""

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
    APIFY_API_KEY,
    FETCH_OPTIONS,
    FETCH_INTERVAL_MINUTES,
    LLM_PROVIDER_ORDER,
    LOG_FILE,
)
from modules import fetcher, llm, formatter, sender
from modules.db import db
from modules.dispatcher import get_dispatcher
from modules.dedup import seen_manager

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def log_pipeline_run(
    start_time: datetime,
    articles_fetched: int,
    sent_count: int,
    llm_calls: int,
    duration: float,
):
    """Log a structured pipeline run summary."""
    logger.info(
        f"[Pipeline] Completed: {articles_fetched} fetched, "
        f"{sent_count} sent, {llm_calls} LLM calls, "
        f"{duration:.1f}s total latency"
    )


async def run_pipeline():
    """Execute the full pipeline: fetch -> dedup -> LLM -> Telegram."""
    start_time = datetime.utcnow()
    logger.info(f"[Pipeline] Starting at {start_time.isoformat()}")

    try:
        # 1. Fetch from all enabled sources
        all_articles = await fetcher.fetch_all(FETCH_OPTIONS)

        if not all_articles:
            logger.info("[Pipeline] No articles fetched from any source")
            return

        logger.info(f"[Pipeline] Fetched {len(all_articles)} articles")

        # 2. Deduplication (using SQLite state db)
        new_articles = seen_manager.filter_new(all_articles)

        if not new_articles:
            logger.info("[Pipeline] No new articles (all duplicates)")
            return

        # 3. Keyword relevance filtering
        relevant = seen_manager.filter_by_keywords(new_articles)

        if not relevant:
            logger.info("[Pipeline] No AI-relevant articles")
            return

        # Limit article count
        relevant = relevant[: config.MAX_ARTICLES_PER_RUN]

        # 4. Mark as seen to prevent duplicate processing
        for article in relevant:
            seen_manager.mark_seen(
                article.url_hash, article.url, getattr(article, "source", "unknown")
            )

        # 5. LLM summarization (batched for efficiency)
        summaries = await llm.summarise_all_flex(relevant, LLM_PROVIDER_ORDER)

        if not summaries:
            logger.warning("[Pipeline] No summaries generated")
            return

        # 6. Score filtering
        high_score = llm.filter_by_score(summaries)

        if not high_score:
            logger.info("[Pipeline] No articles passed relevance threshold")
            return

        # 7. Format and send to Telegram
        messages = formatter.format_batch(high_score)

        if not messages:
            logger.warning("[Pipeline] No messages formatted")
            return

        sent_count = await sender.send_batch(messages)
        llm_calls = llm.get_daily_call_count()
        duration = (datetime.utcnow() - start_time).total_seconds()

        # 8. Log delivery
        for article in relevant:
            db.log_delivery(
                article.url,
                article.title,
                TELEGRAM_CHAT_ID,
                "sent" if sent_count > 0 else "failed",
            )

        log_pipeline_run(start_time, len(relevant), sent_count, llm_calls, duration)
        logger.info(f"[Pipeline] Complete in {duration:.1f}s")

    except Exception as e:
        logger.error(f"[Pipeline] Error: {e}", exc_info=True)
        db.log_error("pipeline", str(e), "run_pipeline")
    except asyncio.CancelledError:
        logger.info("[Pipeline] Cancelled, shutting down...")


async def run_apify_only():
    """For testing: fetch only from Apify (Twitter + Reddit)."""

    from modules.apify_fetcher import ApifyFetcher

    logger.info("[Apify] Starting Apify-only fetch...")

    try:
        async with ApifyFetcher() as fetcher:
            # Fetch Twitter
            if FETCH_OPTIONS.get("apify_twitter"):
                tweets = await fetcher.fetch_twitter(config.TWITTER_ACCOUNTS)
                logger.info(f"[Apify] Twitter: {len(tweets)} relevant tweets")

            # Fetch Reddit
            if FETCH_OPTIONS.get("apify_reddit"):
                posts = await fetcher.fetch_reddit(config.REDDIT_SUBREDDITS)
                logger.info(f"[Apify] Reddit: {len(posts)} relevant posts")

    except Exception as e:
        logger.error(f"[Apify] Error: {e}", exc_info=True)


def setup_scheduler():
    """Configure APScheduler for periodic execution."""
    scheduler = AsyncIOScheduler()

    # Primary pipeline job (includes Apify now via fetcher.fetch_all)
    scheduler.add_job(
        run_pipeline,
        "interval",
        minutes=FETCH_INTERVAL_MINUTES,
        id="ai_news_pipeline",
        name="main_pipeline",
        next_run_time=datetime.utcnow(),
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"[Scheduler] Started, primary interval: {FETCH_INTERVAL_MINUTES} minutes"
    )

    return scheduler


async def main():
    """Main entry point."""
    # Ensure directories exist
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.LOG_DIR, exist_ok=True)

    # Validate critical config
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
            "No LLM provider available. Set at least one API key: GEMINI_API_KEY, NVIDIA_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY"
        )
        sys.exit(1)

    logger.info(f"[LLM] Using provider: {provider}")
    logger.info("[Main] AI News Bot starting...")

    # Start scheduler and run
    scheduler = setup_scheduler()

    # Run pipeline immediately on startup
    await run_pipeline()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("[Main] Shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
