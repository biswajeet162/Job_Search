import traceback
from concurrent.futures import ThreadPoolExecutor

from app.companies.registry import CompanyServiceRegistry
from app.config.config_loader import ConfigLoader
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.crawl_result import CrawlExecutionResult, ErrorRecord
from app.services.storage_service import StorageService
from app.utils.datetime_util import now_iso, utc_now
from app.utils.hash_util import generate_execution_id
from app.utils.logger import get_crawler_logger, get_logger

logger = get_logger(__name__)


class CrawlService:
    """Orchestrates company crawl services with error handling and persistence."""

    def __init__(
        self,
        settings: Settings,
        config_loader: ConfigLoader,
        storage_service: StorageService,
        company_registry: CompanyServiceRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._config_loader = config_loader
        self._storage_service = storage_service
        self._company_registry = company_registry or CompanyServiceRegistry(settings)
        self._executor = ThreadPoolExecutor(
            max_workers=config_loader.load().scheduler.max_workers
        )
        self._active_executions: set[str] = set()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def submit_crawl(self, company: CompanyConfig) -> None:
        self._executor.submit(self._execute_crawl_safe, company)

    def trigger_manual_crawl(self, company_id: str) -> CrawlExecutionResult | None:
        company = self._config_loader.get_company(company_id)
        if company is None:
            return None
        return self._execute_crawl_safe(company)

    def _execute_crawl_safe(self, company: CompanyConfig) -> CrawlExecutionResult:
        started = utc_now()
        execution_id = generate_execution_id(company.id, started)
        crawl_logger = get_crawler_logger(__name__, execution_id, company.name)

        if execution_id in self._active_executions:
            crawl_logger.warning("Duplicate execution skipped")
            return CrawlExecutionResult(
                execution_id=execution_id,
                company_id=company.id,
                success=False,
                error_message="Duplicate execution in progress",
            )

        self._active_executions.add(execution_id)
        crawl_logger.info("%s crawl service started", company.name)

        try:
            company_service = self._company_registry.create(company)
            document = company_service.run(execution_id=execution_id, started_at=started)
            file_path = self._storage_service.store_crawl_result(document, dt=started)

            crawl_logger.info("%d jobs fetched", document.statistics.total_jobs)
            crawl_logger.info(
                "Crawl completed successfully in %d ms",
                document.crawler.duration_ms,
            )

            return CrawlExecutionResult(
                execution_id=execution_id,
                company_id=company.id,
                success=True,
                total_jobs=document.statistics.total_jobs,
                file_path=str(file_path),
            )
        except Exception as exc:
            crawl_logger.error("%s: %s", type(exc).__name__, exc)
            crawl_logger.debug(traceback.format_exc())

            error_record = ErrorRecord(
                execution_id=execution_id,
                company=company.id,
                timestamp=now_iso(),
                error_type=type(exc).__name__,
                message=str(exc),
                stacktrace=traceback.format_exc(),
            )
            self._storage_service.store_error(error_record, dt=started)

            return CrawlExecutionResult(
                execution_id=execution_id,
                company_id=company.id,
                success=False,
                error_message=str(exc),
            )
        finally:
            self._active_executions.discard(execution_id)
