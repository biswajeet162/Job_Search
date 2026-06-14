from pathlib import Path

from app.config.settings import Settings
from app.models.crawl_result import CrawlHistoryEntry, ErrorRecord
from app.models.job import CrawlResultDocument
from app.services.file_service import FileService
from app.utils.datetime_util import format_date_folder, format_time_filename, utc_now
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Persists crawl results and error records to the filesystem."""

    def __init__(self, settings: Settings, file_service: FileService | None = None) -> None:
        self._settings = settings
        self._file_service = file_service or FileService()

    @property
    def storage_dir(self) -> Path:
        assert self._settings.storage_dir is not None
        return self._settings.storage_dir

    @property
    def errors_dir(self) -> Path:
        assert self._settings.errors_dir is not None
        return self._settings.errors_dir

    def _build_execution_path(
        self,
        base_dir: Path,
        company_id: str,
        dt=None,
    ) -> Path:
        """Build path: {base}/{company_id}/{DD-MM-YYYY}/{HH-MM-SS}.json"""
        current = dt or utc_now()
        date_folder = format_date_folder(current)
        time_filename = format_time_filename(current)
        return base_dir / company_id / date_folder / f"{time_filename}.json"

    def store_crawl_result(self, document: CrawlResultDocument, dt=None) -> Path:
        """Store a successful crawl execution document."""
        file_path = self._build_execution_path(
            self.storage_dir,
            document.company.id,
            dt=dt,
        )
        self._file_service.write_json(file_path, document.model_dump())
        logger.info(
            "JSON file stored successfully at %s",
            file_path,
            extra={"execution_id": document.execution_id, "company": document.company.name},
        )
        return file_path

    def store_error(self, error: ErrorRecord, dt=None) -> Path:
        """Store an error record for a failed crawl execution."""
        file_path = self._build_execution_path(
            self.errors_dir,
            error.company,
            dt=dt,
        )
        self._file_service.write_json(file_path, error.model_dump())
        logger.error(
            "Error JSON stored at %s: %s - %s",
            file_path,
            error.error_type,
            error.message,
            extra={"execution_id": error.execution_id, "company": error.company},
        )
        return file_path

    def get_recent_history(
        self,
        company_id: str,
        limit: int = 20,
    ) -> list[CrawlHistoryEntry]:
        """Return recent crawl history entries for a company."""
        company_dir = self.storage_dir / company_id
        if not company_dir.exists():
            return []

        entries: list[CrawlHistoryEntry] = []

        for date_dir in reversed(self._file_service.list_date_directories(company_dir)):
            json_files = sorted(date_dir.glob("*.json"), reverse=True)
            for json_file in json_files:
                try:
                    data = self._file_service.read_json(json_file)
                    crawler_info = data.get("crawler", {})
                    statistics = data.get("statistics", {})
                    entries.append(
                        CrawlHistoryEntry(
                            execution_id=data.get("execution_id", json_file.stem),
                            file_name=json_file.name,
                            file_path=str(json_file),
                            timestamp=crawler_info.get("completed_at", ""),
                            status=crawler_info.get("status", "UNKNOWN"),
                            total_jobs=statistics.get("total_jobs"),
                        )
                    )
                except (OSError, ValueError, KeyError) as exc:
                    logger.warning("Skipping unreadable history file %s: %s", json_file, exc)

                if len(entries) >= limit:
                    return entries

        return entries
