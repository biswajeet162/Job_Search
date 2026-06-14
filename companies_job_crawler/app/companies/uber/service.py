from urllib.parse import urljoin

from bs4 import Tag

from app.companies.base.fetcher import BaseJobFetcher
from app.companies.base.mapper import BaseJobMapper
from app.companies.base.parser import BaseJobParser
from app.companies.base.company_service import BaseCompanyCrawlService
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.models.job import Job


class UberFetcher(BaseJobFetcher):
    def fetch(self) -> str:
        return self._http_get().text


class UberParser(BaseJobParser):
    """
    Parses Uber careers listing structure.

    Native fields: posting_id, roleTitle, listingUrl, team, job_description.
    """

    def __init__(self, company: CompanyConfig) -> None:
        self.company = company

    def parse(self, raw_payload: str) -> list[dict]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_payload, "html.parser")
        records: list[dict] = []

        for anchor in soup.select('a[href*="/careers/list/"], a[href*="/jobs/"]'):
            record = self._extract_native_record(anchor)
            if record:
                records.append(record)

        return records

    def _extract_native_record(self, anchor: Tag) -> dict | None:
        if not isinstance(anchor, Tag):
            return None

        title = anchor.get_text(strip=True)
        href = str(anchor.get("href", ""))
        if not title or not href:
            return None

        parent = anchor.find_parent(["li", "div"])
        team_el = parent.find(class_=lambda c: c and "team" in str(c).lower()) if parent else None
        desc_el = parent.find(class_=lambda c: c and "description" in str(c).lower()) if parent else None

        posting_id = anchor.get("data-posting-id") or anchor.get("data-job-id")
        if not posting_id and "/list/" in href:
            posting_id = href.rstrip("/").split("/")[-1]

        return {
            "posting_id": posting_id,
            "roleTitle": title,
            "listingUrl": urljoin(str(self.company.url), href),
            "team": team_el.get_text(strip=True) if team_el else None,
            "job_description": desc_el.get_text(strip=True) if desc_el else None,
        }


class UberJobMapper(BaseJobMapper):
    """Maps Uber native fields (posting_id, roleTitle, listingUrl) to Job."""

    def map_to_job(self, native_job: dict) -> Job | None:
        title = self._resolve_title(native_job, "roleTitle", "jobTitle", "title", "job_title")
        url = self._resolve_url(native_job, "listingUrl", "url", "applyUrl", "link")
        if not title or not url:
            return None
        job_id = self._resolve_job_id(
            native_job,
            "posting_id",
            "postingId",
            "jobId",
            "work_id",
            url=url,
            title=title,
        )
        return Job(job_id=job_id, job_title=title, job_url=url, raw_data=native_job)


class UberCrawlService(BaseCompanyCrawlService):
    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        super().__init__(
            company=company,
            settings=settings,
            fetcher=UberFetcher(company, settings),
            parser=UberParser(company),
            mapper=UberJobMapper(company, settings),
        )
