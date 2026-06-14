from abc import ABC, abstractmethod
from typing import Any

import requests

from app.config.settings import Settings
from app.models.company import CompanyConfig


class BaseJobFetcher(ABC):
    """Fetches raw payload from a company career source."""

    USER_AGENT = (
        "Mozilla/5.0 (compatible; JobCrawlerEngine/1.0; +https://github.com/job-intelligence)"
    )

    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        self.company = company
        self.settings = settings
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})

    @abstractmethod
    def fetch(self) -> Any:
        """Return raw payload (HTML string, JSON dict, etc.)."""

    def _http_get(self, url: str | None = None) -> requests.Response:
        target = url or str(self.company.url)
        response = self._session.get(
            target,
            timeout=self.settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return response
