from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.companies.generic.service import GenericCompanyCrawlService
from app.companies.registry import CompanyServiceRegistry
from app.config.settings import Settings
from app.models.company import CompanyConfig


@pytest.fixture
def company() -> CompanyConfig:
    return CompanyConfig(
        id="testco",
        name="Test Company",
        enabled=True,
        interval_minutes=15,
        offset_minutes=0,
        crawler_type="html",
        url="https://example.com/careers",
    )


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        project_root=tmp_path,
        max_retries=1,
        request_timeout_seconds=5,
    )


def test_generic_parser_and_mapper_via_service(company: CompanyConfig, settings: Settings) -> None:
    service = GenericCompanyCrawlService(company, settings)
    html = """
    <html>
      <body>
        <a href="/jobs/engineer">Software Engineer</a>
        <a href="/about">About Us</a>
        <a href="/careers/designer">Product Designer Role</a>
      </body>
    </html>
    """
    native_jobs = service.parser.parse(html)
    jobs = service.mapper.map_many(native_jobs)

    assert len(jobs) == 2
    assert all(job.job_id for job in jobs)
    assert all(job.raw_data for job in jobs)


def test_crawler_factory_creates_company_service(settings: Settings, company: CompanyConfig) -> None:
    from app.crawler.crawler_factory import CrawlerFactory
    from app.companies.mastercard.service import MastercardCrawlService

    factory = CrawlerFactory(settings)
    mastercard = CompanyConfig(
        id="mastercard",
        name="Mastercard",
        url="https://careers.mastercard.com",
    )
    service = factory.create(mastercard)
    assert isinstance(service, MastercardCrawlService)

    generic = factory.create(company)
    assert isinstance(generic, GenericCompanyCrawlService)
