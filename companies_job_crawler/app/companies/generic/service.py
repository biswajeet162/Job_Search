from app.companies.base.company_service import BaseCompanyCrawlService
from app.companies.generic.components import GenericHtmlFetcher, GenericHtmlParser, GenericJobMapper
from app.config.settings import Settings
from app.models.company import CompanyConfig


class GenericCompanyCrawlService(BaseCompanyCrawlService):
    """
    Default crawl service for companies without a dedicated module.

    Used when a company is defined in YAML only.
    """

    def __init__(self, company: CompanyConfig, settings: Settings) -> None:
        super().__init__(
            company=company,
            settings=settings,
            fetcher=GenericHtmlFetcher(company, settings),
            parser=GenericHtmlParser(company),
            mapper=GenericJobMapper(company, settings),
        )
