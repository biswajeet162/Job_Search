from urllib.parse import urljoin

from bs4 import Tag

from app.companies.base.fetcher import BaseJobFetcher
from app.companies.base.mapper import BaseJobMapper
from app.companies.base.parser import BaseJobParser
from app.companies.base.company_service import BaseCompanyCrawlService
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.job import Job


class VisaFetcher(BaseJobFetcher):
    def fetch(self) -> str:
        return self._http_get().text


class VisaParser(BaseJobParser):
    """
    Parses Visa / Workday-style career page elements.

    Native fields: work_id, jobTitle, externalUrl, jobDescription, location.
    """

    def __init__(self, company: CompanyConfig) -> None:
        self.company = company

    def parse(self, raw_payload: str) -> list[dict]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_payload, "html.parser")
        records: list[dict] = []

        for element in soup.select('[data-automation-id="jobTitle"], .job-title, .job-link'):
            record = self._extract_native_record(element)
            if record:
                records.append(record)

        return records

    def _extract_native_record(self, element: Tag) -> dict | None:
        anchor = element if element.name == "a" else element.find("a", href=True)
        if not anchor or not isinstance(anchor, Tag):
            return None

        title = anchor.get_text(strip=True)
        href = str(anchor.get("href", ""))
        if not title or not href:
            return None

        parent = element.find_parent(["li", "div", "tr"])
        description_el = None
        location_el = None
        if parent:
            description_el = parent.find(class_=lambda c: c and "description" in str(c).lower())
            location_el = parent.find(class_=lambda c: c and "location" in str(c).lower())

        return {
            "work_id": element.get("data-job-id") or anchor.get("data-job-id"),
            "jobTitle": title,
            "externalUrl": urljoin(str(self.company.url), href),
            "jobDescription": description_el.get_text(strip=True) if description_el else None,
            "location": location_el.get_text(strip=True) if location_el else None,
            "automation_id": element.get("data-automation-id"),
        }


class VisaJobMapper(BaseJobMapper):
    """Maps Visa native fields (work_id, jobTitle, externalUrl) to Job."""

    def map_to_job(self, native_job: dict) -> Job | None:
        title = self._resolve_title(native_job, "jobTitle", "title", "job_title", "positionTitle")
        url = self._resolve_url(native_job, "externalUrl", "url", "applyUrl", "link")
        if not title or not url:
            return None
        job_id = self._resolve_job_id(
            native_job,
            "work_id",
            "workId",
            "jobId",
            "requisitionId",
            url=url,
            title=title,
        )
        return Job(job_id=job_id, job_title=title, job_url=url, raw_data=native_job)


class VisaCrawlService(BaseCompanyCrawlService):
    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        super().__init__(
            company=company,
            settings=settings,
            fetcher=VisaFetcher(company, settings),
            parser=VisaParser(company),
            mapper=VisaJobMapper(company, settings),
        )
