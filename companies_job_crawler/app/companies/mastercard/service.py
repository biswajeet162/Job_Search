from urllib.parse import urljoin

from bs4 import Tag

from app.companies.base.fetcher import BaseJobFetcher
from app.companies.base.mapper import BaseJobMapper
from app.companies.base.parser import BaseJobParser
from app.companies.base.company_service import BaseCompanyCrawlService
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.job import Job


class MastercardFetcher(BaseJobFetcher):
    def fetch(self) -> str:
        return self._http_get().text


class MastercardParser(BaseJobParser):
    """
    Parses Mastercard-specific HTML structure.

    Native fields: requisitionId, jobTitle, applyUrl, location, department.
    """

    def __init__(self, company: CompanyConfig) -> None:
        self.company = company

    def parse(self, raw_payload: str) -> list[dict]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_payload, "html.parser")
        records: list[dict] = []

        selectors = [
            ("a", {"class": lambda c: c and "job" in str(c).lower()}),
            ("div", {"class": lambda c: c and "job-result" in str(c).lower()}),
        ]

        for tag_name, attrs in selectors:
            for element in soup.find_all(tag_name, attrs):
                record = self._extract_native_record(element)
                if record:
                    records.append(record)

        return records

    def _extract_native_record(self, element: Tag) -> dict | None:
        anchor = element if element.name == "a" else element.find("a", href=True)
        if not anchor or not isinstance(anchor, Tag):
            return None

        title = anchor.get_text(strip=True) or element.get_text(strip=True)
        href = str(anchor.get("href", ""))
        if not title or not href:
            return None

        requisition_id = element.get("data-job-id") or element.get("data-requisition-id")
        location_el = element.find(class_=lambda c: c and "location" in str(c).lower())
        dept_el = element.find(class_=lambda c: c and "department" in str(c).lower())

        return {
            "requisitionId": requisition_id,
            "jobTitle": title,
            "applyUrl": urljoin(str(self.company.url), href),
            "location": location_el.get_text(strip=True) if location_el else None,
            "department": dept_el.get_text(strip=True) if dept_el else None,
            "html_tag": element.name,
            "classes": element.get("class", []),
        }


class MastercardJobMapper(BaseJobMapper):
    """Maps Mastercard native fields (requisitionId, jobTitle, applyUrl) to Job."""

    def map_to_job(self, native_job: dict) -> Job | None:
        title = self._resolve_title(native_job, "jobTitle", "title", "job_title")
        url = self._resolve_url(native_job, "applyUrl", "url", "link")
        if not title or not url:
            return None
        job_id = self._resolve_job_id(
            native_job,
            "requisitionId",
            "jobId",
            "job_id",
            url=url,
            title=title,
        )
        return Job(job_id=job_id, job_title=title, job_url=url, raw_data=native_job)


class MastercardCrawlService(BaseCompanyCrawlService):
    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        super().__init__(
            company=company,
            settings=settings,
            fetcher=MastercardFetcher(company, settings),
            parser=MastercardParser(company),
            mapper=MastercardJobMapper(company, settings),
        )
