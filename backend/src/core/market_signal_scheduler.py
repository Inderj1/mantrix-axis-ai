"""
Market Signal Scheduler
Background task for periodically fetching and updating market intelligence signals
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog

from .market_signal_service import get_market_signal_service
from .fetchers import (
    WeatherSignalFetcher,
    EconomicSignalFetcher,
    NewsSignalFetcher,
    RegulatorySignalFetcher,
    EnergySignalFetcher,
    LaborSignalFetcher
)
from ..db.market_signals_db import get_market_signals_db
from ..models.market_signal import SignalCategory

logger = structlog.get_logger()


class MarketSignalScheduler:
    """
    Background scheduler for fetching market signals
    Runs periodically to update signals from various data sources
    """

    def __init__(self, check_interval: int = 3600):  # Default: 1 hour
        self.check_interval = check_interval  # seconds
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.logger = logger.bind(component="MarketSignalScheduler")
        self._db_available = True

        # Initialize services
        self.signal_service = get_market_signal_service()

        # Try to initialize MongoDB - if it fails, scheduler will run in degraded mode
        self.db = get_market_signals_db()
        if self.db is None:
            self._db_available = False
            self.logger.warning("scheduler_degraded_mode",
                message="MongoDB not available, market signal scheduler will not persist signals")

        # Track last fetch times
        self.last_fetch_times = {}

        # Register fetchers
        self._register_fetchers()

    def _register_fetchers(self):
        """Register all available signal fetchers"""
        # Weather fetcher - update every 30 minutes
        weather_fetcher = WeatherSignalFetcher()
        self.signal_service.register_fetcher(weather_fetcher)
        self.last_fetch_times[SignalCategory.WEATHER] = None

        # Economic fetcher - update every 4 hours
        economic_fetcher = EconomicSignalFetcher()
        self.signal_service.register_fetcher(economic_fetcher)
        self.last_fetch_times[SignalCategory.ECONOMIC] = None

        # News fetcher - update every 1 hour
        news_fetcher = NewsSignalFetcher()
        self.signal_service.register_fetcher(news_fetcher)
        self.last_fetch_times[SignalCategory.NEWS] = None

        # Regulatory fetcher - update every 6 hours
        regulatory_fetcher = RegulatorySignalFetcher()
        self.signal_service.register_fetcher(regulatory_fetcher)
        self.last_fetch_times[SignalCategory.REGULATORY] = None

        # Energy fetcher - update every 24 hours
        energy_fetcher = EnergySignalFetcher()
        self.signal_service.register_fetcher(energy_fetcher)
        self.last_fetch_times[SignalCategory.ENERGY] = None

        # Labor fetcher - update every 24 hours
        labor_fetcher = LaborSignalFetcher()
        self.signal_service.register_fetcher(labor_fetcher)
        self.last_fetch_times[SignalCategory.LABOR] = None

        self.logger.info("fetchers_registered", count=6)

    async def start(self):
        """Start the background scheduler"""
        if self.is_running:
            self.logger.warning("scheduler_already_running")
            return

        self.is_running = True
        self.logger.info("scheduler_started", check_interval=self.check_interval)

        # Run initial fetch immediately
        await self._fetch_and_store_signals()

        # Start periodic checking
        while self.is_running:
            try:
                await asyncio.sleep(self.check_interval)
                if self.is_running:
                    await self._fetch_and_store_signals()
            except asyncio.CancelledError:
                self.logger.info("scheduler_cancelled")
                break
            except Exception as e:
                self.logger.error("scheduler_error", error=str(e), exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def stop(self):
        """Stop the background scheduler"""
        self.logger.info("stopping_scheduler")
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _fetch_and_store_signals(self):
        """Fetch signals from all sources and store in database"""
        # Skip if database is not available
        if not self._db_available or self.db is None:
            self.logger.debug("skipping_signal_fetch", reason="MongoDB not available")
            return

        start_time = datetime.utcnow()
        self.logger.info("starting_signal_fetch", timestamp=start_time.isoformat())

        try:
            # Determine which categories need updating based on refresh intervals
            categories_to_fetch = self._get_categories_to_update()

            if not categories_to_fetch:
                self.logger.info("no_categories_need_update")
                return

            # Fetch signals
            signals = await self.signal_service.fetch_all_signals(categories_to_fetch)

            if not signals:
                self.logger.warning("no_signals_fetched")
                return

            # Store in database
            result = self.db.insert_signals_bulk(signals)

            # Update last fetch times
            for category in categories_to_fetch:
                self.last_fetch_times[category] = datetime.utcnow()

            # Calculate metrics
            duration = (datetime.utcnow() - start_time).total_seconds()

            self.logger.info(
                "signal_fetch_complete",
                duration_seconds=duration,
                categories_fetched=len(categories_to_fetch),
                total_signals=len(signals),
                inserted=result["inserted"],
                duplicates=result["duplicates"],
                errors=result["errors"]
            )

            # Optional: Cleanup old signals
            if datetime.utcnow().hour == 2:  # Run cleanup at 2 AM
                deleted = self.db.cleanup_old_signals(days_old=30)
                self.logger.info("old_signals_cleanup", deleted_count=deleted)

        except Exception as e:
            self.logger.error("fetch_and_store_error", error=str(e), exc_info=True)

    def _get_categories_to_update(self) -> list:
        """
        Determine which categories need updating based on refresh intervals
        """
        now = datetime.utcnow()
        categories_to_fetch = []

        # Define refresh intervals for each category (in minutes)
        refresh_intervals = {
            SignalCategory.WEATHER: 30,        # Weather: every 30 min
            SignalCategory.ECONOMIC: 240,      # Economic: every 4 hours
            SignalCategory.NEWS: 60,           # News: every hour
            SignalCategory.REGULATORY: 360,    # Regulatory: every 6 hours
            SignalCategory.ENERGY: 1440,       # Energy: every 24 hours
            SignalCategory.LABOR: 1440,        # Labor: every 24 hours
        }

        for category, interval_minutes in refresh_intervals.items():
            last_fetch = self.last_fetch_times.get(category)

            if last_fetch is None:
                # Never fetched, needs update
                categories_to_fetch.append(category)
            else:
                time_since_fetch = (now - last_fetch).total_seconds() / 60
                if time_since_fetch >= interval_minutes:
                    categories_to_fetch.append(category)

        self.logger.info(
            "categories_for_update",
            total=len(categories_to_fetch),
            categories=[c.value for c in categories_to_fetch]
        )

        return categories_to_fetch

    async def force_refresh(self, category: Optional[SignalCategory] = None):
        """
        Force an immediate refresh of signals
        If category is specified, only refresh that category
        """
        if not self._db_available or self.db is None:
            self.logger.warning("force_refresh_skipped", reason="MongoDB not available")
            return

        self.logger.info("force_refresh_triggered", category=category.value if category else "all")

        if category:
            signals = await self.signal_service.fetch_signals_for_category(category)
            if signals:
                self.db.insert_signals_bulk(signals)
                self.last_fetch_times[category] = datetime.utcnow()
        else:
            await self._fetch_and_store_signals()

        self.logger.info("force_refresh_complete")

    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "check_interval_seconds": self.check_interval,
            "last_fetch_times": {
                cat.value: time.isoformat() if time else None
                for cat, time in self.last_fetch_times.items()
            },
            "registered_fetchers": len(self.signal_service.fetchers)
        }


# Singleton instance
_scheduler_instance: Optional[MarketSignalScheduler] = None


def get_market_signal_scheduler(check_interval: int = 3600) -> MarketSignalScheduler:
    """Get or create the singleton MarketSignalScheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = MarketSignalScheduler(check_interval)
    return _scheduler_instance
