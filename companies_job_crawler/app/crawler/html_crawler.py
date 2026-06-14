from typing import Any

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.config.settings import Settings
from app.crawler.base_crawler import BaseCrawler
from app.models.company import CompanyConfig
from app.models.job import Job


class HtmlCrawler(BaseCrawler):
    """
    Generic HTML crawler using requests + BeautifulSoup.

    Company-specific crawlers extend this and override parse_jobs().
    """

    def fetch_jobs(self) -> str:
        response = self._http_get()
        return response.text

    def parse_jobs(self, raw_data: str) -> list[Job]:
        soup = self._parse_html(raw_data)
        return self._extract_generic_job_links(soup)

    def _extract_generic_job_links(self, soup: BeautifulSoup) -> list[Job]:
        """Fallback parser: extract links that look like job postings."""
        jobs: list[Job] = []
        keywords = ("job", "career", "position", "opening", "vacancy", "role")

        for anchor in soup.find_all("a", href=True):
            if not isinstance(anchor, Tag):
                continue
            href = anchor.get("href", "")
            title = anchor.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            href_lower = str(href).lower()
            title_lower = title.lower()
            if not any(keyword in href_lower or keyword in title_lower for keyword in keywords):
                continue
            url = self._resolve_url(str(href))
            jobs.append(
                self._build_job(
                    title=title,
                    url=url,
                    raw_data={
                        "source": "generic_link_extraction",
                        "href": href,
                        "text": title,
                    },
                )
            )

        return self._deduplicate_jobs(jobs)

    def _resolve_url(self, href: str) -> str:
        """Resolve relative URLs against the company base URL."""
        return urljoin(str(self.company.url), href)


class PlaywrightCrawler(HtmlCrawler):
    """
    Playwright-compatible crawler placeholder.

    Currently falls back to HTTP fetch. Future implementations will use
    Playwright for JavaScript-rendered career pages.
    """

    def fetch_jobs(self) -> str:
        # Playwright integration point: swap HTTP fallback when browser automation is added.
        return super().fetch_jobs()
