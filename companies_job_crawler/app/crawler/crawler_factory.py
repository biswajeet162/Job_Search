"""
Legacy crawler factory — delegates to CompanyServiceRegistry.

Prefer using app.companies.registry.CompanyServiceRegistry directly.
"""

from app.companies.registry import CompanyServiceRegistry
from app.config.settings import Settings
from app.models.company import CompanyConfig


class CrawlerFactory:
    """Backward-compatible wrapper around company crawl services."""

    def __init__(self, settings: Settings) -> None:
        self._registry = CompanyServiceRegistry(settings)

    def create(self, company: CompanyConfig):
        return self._registry.create(company)

    def register_company_crawler(self, company_id: str, service_cls) -> None:
        self._registry.register(company_id, service_cls)
