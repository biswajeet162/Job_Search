from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.companies.base.fetcher import BaseJobFetcher
from app.companies.base.mapper import BaseJobMapper
from app.companies.base.parser import BaseJobParser
from app.models.company import CompanyConfig
from app.models.job import Job


class GenericHtmlFetcher(BaseJobFetcher):
    """Default HTTP fetcher for HTML career pages."""

    def fetch(self) -> str:
        return self._http_get().text


class GenericHtmlParser(BaseJobParser):
    """Fallback parser using job/career keyword link heuristics."""

    KEYWORDS = ("job", "career", "position", "opening", "vacancy", "role")

    def __init__(self, company: CompanyConfig) -> None:
        self.company = company

    def parse(self, raw_payload: str) -> list[dict]:
        soup = BeautifulSoup(raw_payload, "html.parser")
        records: list[dict] = []

        for anchor in soup.find_all("a", href=True):
            if not isinstance(anchor, Tag):
                continue
            href = str(anchor.get("href", ""))
            title = anchor.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            href_lower = href.lower()
            title_lower = title.lower()
            if not any(k in href_lower or k in title_lower for k in self.KEYWORDS):
                continue
            records.append(
                {
                    "link": urljoin(str(self.company.url), href),
                    "text": title,
                    "href": href,
                    "source": "generic_link_extraction",
                }
            )
        return records


class GenericJobMapper(BaseJobMapper):
    """Maps generic link records to standardized jobs."""

    def map_to_job(self, native_job: dict) -> Job | None:
        title = self._resolve_title(native_job, "text", "title", "jobTitle", "job_title")
        url = self._resolve_url(native_job, "link", "url", "applyUrl", "job_url")
        if not title or not url:
            return None
        job_id = self._resolve_job_id(
            native_job,
            "jobId",
            "job_id",
            "work_id",
            "requisitionId",
            url=url,
            title=title,
        )
        return Job(
            job_id=job_id,
            job_title=title,
            job_url=url,
            raw_data=native_job,
        )
