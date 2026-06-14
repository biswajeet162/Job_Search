from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from app.companies.registry import CompanyServiceRegistry
from app.config.config_loader import ConfigLoader
from app.config.settings import Settings
from app.models.company import CompanyConfig
from app.services.crawl_service import CrawlService
from app.services.file_service import FileService
from app.services.storage_service import StorageService


@pytest.fixture
def crawl_service(tmp_path) -> CrawlService:
    settings = Settings(
        project_root=tmp_path,
        config_path=tmp_path / "companies.yaml",
        storage_dir=tmp_path / "storage",
        errors_dir=tmp_path / "errors",
        max_retries=1,
    )
    company = CompanyConfig(
        id="failco",
        name="Fail Company",
        url="https://example.com",
    )
    settings.config_path.write_text(
        f"companies:\n  - id: failco\n    name: Fail Company\n    url: https://example.com\n",
        encoding="utf-8",
    )
    loader = ConfigLoader(settings)
    storage = StorageService(settings, FileService())
    return CrawlService(settings, loader, storage, CompanyServiceRegistry(settings))


def test_crawl_service_stores_error_on_failure(crawl_service: CrawlService, tmp_path) -> None:
    company = CompanyConfig(
        id="failco",
        name="Fail Company",
        url="https://example.com",
    )

    with patch.object(
        crawl_service._company_registry,
        "create",
        side_effect=RuntimeError("Simulated crawler failure"),
    ):
        result = crawl_service.trigger_manual_crawl("failco")

    assert result is not None
    assert result.success is False
    assert "Simulated crawler failure" in (result.error_message or "")

    error_files = list((tmp_path / "errors" / "failco").rglob("*.json"))
    assert len(error_files) == 1

    data = FileService().read_json(error_files[0])
    assert data["error_type"] == "RuntimeError"
    assert "Simulated crawler failure" in data["message"]


def test_crawl_service_never_raises(crawl_service: CrawlService) -> None:
    company = CompanyConfig(
        id="failco",
        name="Fail Company",
        url="https://example.com",
    )

    with patch.object(
        crawl_service._company_registry,
        "create",
        side_effect=Exception("Unexpected error"),
    ):
        result = crawl_service._execute_crawl_safe(company)

    assert result.success is False
