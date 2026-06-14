from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.companies.generic.components import GenericHtmlParser, GenericJobMapper
from app.companies.generic.service import GenericCompanyCrawlService
from app.companies.mastercard.service import MastercardJobMapper, MastercardParser
from app.companies.registry import CompanyServiceRegistry
from app.companies.uber.service import UberJobMapper, UberParser
from app.companies.visa.service import VisaJobMapper, VisaParser
from app.config.settings import Settings
from app.models.company import CompanyConfig


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(project_root=tmp_path, max_retries=1)


def test_generic_parser_extracts_native_records() -> None:
    company = CompanyConfig(id="testco", name="Test", url="https://example.com/careers")
    html = """
    <a href="/jobs/engineer">Software Engineer</a>
    <a href="/about">About Us</a>
    """
    records = GenericHtmlParser(company).parse(html)
    assert len(records) == 1
    assert records[0]["text"] == "Software Engineer"
    assert "link" in records[0]


def test_visa_mapper_maps_work_id_and_job_title(settings: Settings) -> None:
    company = CompanyConfig(id="visa", name="Visa", url="https://jobs.visa.com")
    mapper = VisaJobMapper(company, settings)
    job = mapper.map_to_job(
        {
            "work_id": "WRK123",
            "jobTitle": "Data Engineer",
            "externalUrl": "https://jobs.visa.com/job/WRK123",
            "jobDescription": "Build pipelines",
        }
    )
    assert job is not None
    assert job.job_id == "visa_WRK123"
    assert job.job_title == "Data Engineer"
    assert job.raw_data["jobDescription"] == "Build pipelines"


def test_mastercard_mapper_maps_requisition_id(settings: Settings) -> None:
    company = CompanyConfig(id="mastercard", name="Mastercard", url="https://careers.mastercard.com")
    mapper = MastercardJobMapper(company, settings)
    job = mapper.map_to_job(
        {
            "requisitionId": "REQ-99",
            "jobTitle": "Analyst",
            "applyUrl": "https://careers.mastercard.com/jobs/REQ-99",
        }
    )
    assert job is not None
    assert job.job_id == "mastercard_REQ-99"


def test_uber_mapper_maps_posting_id(settings: Settings) -> None:
    company = CompanyConfig(id="uber", name="Uber", url="https://www.uber.com/careers")
    mapper = UberJobMapper(company, settings)
    job = mapper.map_to_job(
        {
            "posting_id": "POST-42",
            "roleTitle": "Backend Engineer",
            "listingUrl": "https://www.uber.com/careers/list/POST-42",
            "job_description": "Ride platform",
        }
    )
    assert job is not None
    assert job.job_id == "uber_POST-42"
    assert job.raw_data["job_description"] == "Ride platform"


def test_company_registry_uses_dedicated_service(settings: Settings) -> None:
    from app.companies.mastercard.service import MastercardCrawlService

    registry = CompanyServiceRegistry(settings)
    company = CompanyConfig(id="mastercard", name="Mastercard", url="https://careers.mastercard.com")
    service = registry.create(company)
    assert isinstance(service, MastercardCrawlService)


def test_company_registry_falls_back_to_generic(settings: Settings) -> None:
    registry = CompanyServiceRegistry(settings)
    company = CompanyConfig(id="newco", name="New Co", url="https://example.com/jobs")
    service = registry.create(company)
    assert isinstance(service, GenericCompanyCrawlService)


def test_company_service_run_lifecycle(settings: Settings) -> None:
    company = CompanyConfig(id="testco", name="Test", url="https://example.com/careers")
    service = GenericCompanyCrawlService(company, settings)
    started = datetime(2026, 6, 14, 10, 0, 0, tzinfo=UTC)

    with patch.object(
        service.fetcher,
        "fetch",
        return_value="<a href='/jobs/1'>Job One</a>",
    ):
        document = service.run(execution_id="testco_20260614_100000", started_at=started)

    assert document.execution_id == "testco_20260614_100000"
    assert document.statistics.total_jobs >= 1
