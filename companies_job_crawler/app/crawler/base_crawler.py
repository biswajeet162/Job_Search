from abc import ABC, abstractmethod
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.job import CompanyInfo, CrawlerInfo, CrawlResultDocument, Job, Statistics
from app.utils.datetime_util import now_iso
from app.utils.hash_util import generate_job_id
from app.utils.logger import get_crawler_logger


class BaseCrawler(ABC):
    """
    Abstract base crawler defining the crawl lifecycle.

    Subclasses implement fetch_jobs() and parse_jobs().
    save_jobs() and run() provide shared orchestration.
    """

    CRAWLER_VERSION = "1.0"
    USER_AGENT = (
        "Mozilla/5.0 (compatible; JobCrawlerEngine/1.0; +https://github.com/job-intelligence)"
    )

    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        self.company = company
        self.settings = settings
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})
        self._logger = None

    def _get_logger(self, execution_id: str):
        if self._logger is None:
            self._logger = get_crawler_logger(
                self.__class__.__name__,
                execution_id,
                self.company.name,
            )
        return self._logger

    @abstractmethod
    def fetch_jobs(self) -> Any:
        """Fetch raw job data from the source (HTML, API response, etc.)."""

    @abstractmethod
    def parse_jobs(self, raw_data: Any) -> list[Job]:
        """Parse raw data into standardized Job models."""

    def save_jobs(
        self,
        jobs: list[Job],
        execution_id: str,
        started_at_iso: str,
        duration_ms: int,
        status: str = "SUCCESS",
    ) -> CrawlResultDocument:
        """Build the crawl result document (persistence handled by CrawlService)."""
        return CrawlResultDocument(
            execution_id=execution_id,
            company=CompanyInfo(id=self.company.id, name=self.company.name),
            crawler=CrawlerInfo(
                started_at=started_at_iso,
                completed_at=now_iso(),
                duration_ms=duration_ms,
                status=status,
                version=self.CRAWLER_VERSION,
            ),
            statistics=Statistics(total_jobs=len(jobs)),
            jobs=jobs,
        )

    def run(self, execution_id: str, started_at) -> CrawlResultDocument:
        """Execute the full crawl lifecycle with retries."""
        started_at_iso = started_at.isoformat()
        logger = self._get_logger(execution_id)
        last_error: Exception | None = None

        for attempt in range(1, self.settings.max_retries + 1):
            start_time = time.perf_counter()
            try:
                raw_data = self.fetch_jobs()
                jobs = self.parse_jobs(raw_data)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info("Parsed %d jobs", len(jobs))
                return self.save_jobs(
                    jobs=jobs,
                    execution_id=execution_id,
                    started_at_iso=started_at_iso,
                    duration_ms=duration_ms,
                )
            except Exception as exc:
                last_error = exc
                logger.error(
                    "%s - Retry attempt %d/%d",
                    type(exc).__name__,
                    attempt,
                    self.settings.max_retries,
                )
                if attempt < self.settings.max_retries:
                    time.sleep(self.settings.retry_delay_seconds)

        raise last_error or RuntimeError("Crawler failed without exception")

    def _http_get(self, url: str | None = None) -> requests.Response:
        """Perform an HTTP GET with configured timeout."""
        target = url or str(self.company.url)
        response = self._session.get(
            target,
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return response

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup."""
        return BeautifulSoup(html, "html.parser")

    def _build_job(
        self,
        title: str,
        url: str,
        raw_data: dict[str, Any] | None = None,
    ) -> Job:
        """Create a Job with standardized fields and preserved raw data."""
        return Job(
            job_id=generate_job_id(self.company.id, url, title),
            job_title=title.strip(),
            job_url=url.strip(),
            raw_data=raw_data or {},
        )

    def _deduplicate_jobs(self, jobs: list[Job]) -> list[Job]:
        """Remove duplicate jobs by job_id while preserving order."""
        seen: set[str] = set()
        unique: list[Job] = []
        for job in jobs:
            if job.job_id not in seen:
                seen.add(job.job_id)
                unique.append(job)
        return unique
