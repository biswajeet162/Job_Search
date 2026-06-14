from app.companies.base.company_service import BaseCompanyCrawlService
from app.companies.generic.service import GenericCompanyCrawlService
from app.companies.mastercard.service import MastercardCrawlService
from app.companies.uber.service import UberCrawlService
from app.companies.visa.service import VisaCrawlService
from app.config.settings import Settings
from app.models.company import CompanyConfig


class CompanyServiceRegistry:
    """
    Registry of company-specific crawl services.

    Each company module owns its fetcher, parser, and mapper.
    YAML-only companies fall back to GenericCompanyCrawlService.
    """

    _SERVICES: dict[str, type[BaseCompanyCrawlService]] = {
        "mastercard": MastercardCrawlService,
        "visa": VisaCrawlService,
        "uber": UberCrawlService,
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, company: CompanyConfig) -> BaseCompanyCrawlService:
        service_cls = self._SERVICES.get(company.id, GenericCompanyCrawlService)
        return service_cls(company=company, settings=self._settings)

    def register(self, company_id: str, service_cls: type[BaseCompanyCrawlService]) -> None:
        """Register a company-specific crawl service (extension point)."""
        self._SERVICES[company_id] = service_cls

    def registered_company_ids(self) -> list[str]:
        return sorted(self._SERVICES.keys())
