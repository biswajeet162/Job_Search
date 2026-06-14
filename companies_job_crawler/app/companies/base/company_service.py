import time
from abc import ABC
from datetime import datetime
from typing import Any

from app.companies.base.fetcher import BaseJobFetcher
from app.companies.base.mapper import BaseJobMapper
from app.companies.base.parser import BaseJobParser
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.job import CompanyInfo, CrawlerInfo, CrawlResultDocument, Statistics
from app.utils.datetime_util import now_iso
from app.utils.logger import get_crawler_logger


class BaseCompanyCrawlService(ABC):
    """
    Company-specific crawl orchestrator.

    Each company module provides its own fetcher, parser, and mapper.
    This base class owns retries, timing, logging, and document assembly.
    """

    SERVICE_VERSION = "1.0"

    def __init__(
        self,
        company: CompanyConfig,
        settings: Settings,
        fetcher: BaseJobFetcher,
        parser: BaseJobParser,
        mapper: BaseJobMapper,
    ) -> None:
        self.company = company
        self.settings = settings
        self.fetcher = fetcher
        self.parser = parser
        self.mapper = mapper
        self._logger = None

    @property
    def company_id(self) -> str:
        return self.company.id

    def _get_logger(self, execution_id: str):
        if self._logger is None:
            self._logger = get_crawler_logger(
                self.__class__.__name__,
                execution_id,
                self.company.name,
            )
        return self._logger

    def run(self, execution_id: str, started_at: datetime) -> CrawlResultDocument:
        started_at_iso = started_at.isoformat()
        logger = self._get_logger(execution_id)
        last_error: Exception | None = None

        for attempt in range(1, self.settings.max_retries + 1):
            start_time = time.perf_counter()
            try:
                raw_payload = self.fetcher.fetch()
                native_jobs = self.parser.parse(raw_payload)
                logger.info("Parsed %d native job records", len(native_jobs))
                jobs = self.mapper.map_many(native_jobs)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info("Mapped %d standardized jobs", len(jobs))
                return self._build_document(
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

        raise last_error or RuntimeError("Company crawl service failed without exception")

    def _build_document(
        self,
        jobs: list[Any],
        execution_id: str,
        started_at_iso: str,
        duration_ms: int,
        status: str = "SUCCESS",
    ) -> CrawlResultDocument:
        return CrawlResultDocument(
            execution_id=execution_id,
            company=CompanyInfo(id=self.company.id, name=self.company.name),
            crawler=CrawlerInfo(
                started_at=started_at_iso,
                completed_at=now_iso(),
                duration_ms=duration_ms,
                status=status,
                version=self.SERVICE_VERSION,
            ),
            statistics=Statistics(total_jobs=len(jobs)),
            jobs=jobs,
        )
