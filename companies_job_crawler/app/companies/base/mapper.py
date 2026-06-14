from abc import ABC, abstractmethod
from typing import Any

from app.companies.base.field_extractor import FieldExtractor
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.job import Job
from app.utils.hash_util import generate_job_id


class BaseJobMapper(ABC):
    """
    Maps company-native job records to the standardized Job model.

    Only job_id, job_title, and job_url are normalized at the top level.
    The full native record is preserved inside raw_data for future AI use.
    """

    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        self.company = company
        self.settings = settings
        self.extractor = FieldExtractor()

    @abstractmethod
    def map_to_job(self, native_job: dict[str, Any]) -> Job | None:
        """Map one native job record to a standardized Job."""

    def map_many(self, native_jobs: list[dict[str, Any]]) -> list[Job]:
        jobs: list[Job] = []
        seen: set[str] = set()
        for native_job in native_jobs:
            job = self.map_to_job(native_job)
            if job is None or job.job_id in seen:
                continue
            seen.add(job.job_id)
            jobs.append(job)
        return jobs

    def _resolve_job_id(self, native_job: dict[str, Any], *id_keys: str, url: str, title: str) -> str:
        native_id = self.extractor.first_present(native_job, *id_keys)
        if native_id is not None:
            return f"{self.company.id}_{native_id}"
        return generate_job_id(self.company.id, url, title)

    def _resolve_title(self, native_job: dict[str, Any], *title_keys: str) -> str | None:
        title = self.extractor.first_present(native_job, *title_keys)
        return str(title).strip() if title else None

    def _resolve_url(self, native_job: dict[str, Any], *url_keys: str) -> str | None:
        url = self.extractor.first_present(native_job, *url_keys)
        return str(url).strip() if url else None
