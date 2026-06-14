from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config.config_loader import ConfigLoader
from app.models.company import CompanyConfig
from app.services.crawl_service import CrawlService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def should_execute_company(company: CompanyConfig, current_minute: int) -> bool:
    """
    Determine if a company crawler should run at the current minute.

    Formula: (current_minute - offset_minutes) % interval_minutes == 0
    """
    if not company.enabled:
        return False
    return (current_minute - company.offset_minutes) % company.interval_minutes == 0


class SchedulerService:
    """Manages the APScheduler tick loop and crawler dispatch."""

    def __init__(
        self,
        config_loader: ConfigLoader,
        crawl_service: CrawlService,
    ) -> None:
        self._config_loader = config_loader
        self._crawl_service = crawl_service
        self._scheduler = BackgroundScheduler(timezone=UTC)
        self._running = False
        self._last_tick: datetime | None = None
        self._last_dispatched: dict[str, str] = {}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_tick(self) -> datetime | None:
        return self._last_tick

    def start(self) -> None:
        """Start the scheduler background loop."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        config = self._config_loader.load()
        tick_seconds = config.scheduler.tick_interval_seconds

        self._scheduler.add_job(
            self._tick,
            trigger=IntervalTrigger(seconds=tick_seconds),
            id="crawler_tick",
            replace_existing=True,
            max_instances=1,
        )
        self._scheduler.start()
        self._running = True
        logger.info(
            "Scheduler started (tick every %d seconds, max_workers=%d)",
            tick_seconds,
            config.scheduler.max_workers,
        )

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._running:
            return
        self._scheduler.shutdown(wait=False)
        self._crawl_service.shutdown()
        self._running = False
        logger.info("Scheduler shutdown complete")

    def _tick(self) -> None:
        """Evaluate all companies and dispatch crawlers without blocking."""
        now = datetime.now(UTC)
        self._last_tick = now
        current_minute = now.minute
        minute_key = now.strftime("%Y%m%d%H%M")

        logger.debug("Scheduler tick at minute %d", current_minute)

        try:
            companies = self._config_loader.get_enabled_companies()
        except Exception as exc:
            logger.error("Failed to load configuration during tick: %s", exc)
            return

        for company in companies:
            try:
                if not should_execute_company(company, current_minute):
                    continue

                dispatch_key = f"{company.id}_{minute_key}"
                if self._last_dispatched.get(company.id) == dispatch_key:
                    continue

                logger.info("Dispatching crawler for %s", company.name)
                self._crawl_service.submit_crawl(company)
                self._last_dispatched[company.id] = dispatch_key
            except Exception as exc:
                logger.error(
                    "Scheduler failed to dispatch %s: %s",
                    company.id,
                    exc,
                    extra={"company": company.name},
                )

    def get_status(self) -> dict:
        """Return scheduler status for the API."""
        config = self._config_loader.load()
        return {
            "running": self._running,
            "last_tick": self._last_tick.isoformat() if self._last_tick else None,
            "tick_interval_seconds": config.scheduler.tick_interval_seconds,
            "max_workers": config.scheduler.max_workers,
            "enabled_companies": len(self._config_loader.get_enabled_companies()),
            "scheduled_jobs": [
                {
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in self._scheduler.get_jobs()
            ],
        }
