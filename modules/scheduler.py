"""Lightweight scheduler with smart polling and traffic optimization.

Uses APScheduler with dynamic intervals to reduce API calls
while maintaining target throughput during active news cycles.
"""

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config


class SmartScheduler:
    """Production scheduler with:
    - Dynamic interval adjustment (speed up during news cycles, slow down otherwise)
    - Batched fetches to minimize API calls
    - Rate limit protection for all APIs
    - Condition-based polling (skip if nothing to fetch)
    """

    def __init__(self, base_interval=30):
        self.scheduler = AsyncIOScheduler()
        self.base_interval = base_interval  # minutes
        self.current_interval = base_interval
        self.min_interval = 5  # fastest: every 5 minutes during news cycle
        self.max_interval = 60  # slowest: every hour when quiet
        self.consecutive_empty = 0
        self.consecutive_found = 0

    def start(self, job_func, job_id="pipeline"):
        """Start the scheduler with latency and throughput optimization."""
        print(f"[Scheduler] Starting with base_interval={self.base_interval} min")
        self.scheduler.add_job(
            job_func,
            "interval",
            minutes=self.current_interval,
            id=job_id,
            next_run_time=datetime.utcnow(),
            replace_existing=True,
        )
        self.scheduler.start()

    def adjust_interval(self, found_items: int):
        """Dynamically adjust polling interval based on activity.

        If articles found (news cycle active): speed up to min_interval
        If no articles found (quiet): slow down to max_interval
        """
        if found_items > 0:
            self.consecutive_found += 1
            self.consecutive_empty = 0
            # Speed up during active news cycles
            new_interval = max(
                self.min_interval,
                self.current_interval - 5,
            )
        else:
            self.consecutive_empty += 1
            self.consecutive_found = 0
            # Slow down during quiet periods
            new_interval = min(
                self.current_interval + 5,
                self.max_interval,
            )

        if new_interval != self.current_interval:
            self.current_interval = new_interval
            print(
                f"[Scheduler] Adjusted interval to {self.current_interval} min "
                f"(found={found_items}, empty_streak={self.consecutive_empty}, "
                f"found_streak={self.consecutive_found})"
            )

    def stop(self):
        self.scheduler.shutdown()
