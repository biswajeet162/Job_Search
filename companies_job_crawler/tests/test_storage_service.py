from datetime import UTC, datetime

import pytest

from app.config.settings import Settings
from app.models.crawl_result import ErrorRecord
from app.models.job import CompanyInfo, CrawlerInfo, CrawlResultDocument, Job, Statistics
from app.services.file_service import FileService
from app.services.storage_service import StorageService


@pytest.fixture
def storage_service(tmp_path) -> StorageService:
    settings = Settings(
        project_root=tmp_path,
        storage_dir=tmp_path / "storage",
        errors_dir=tmp_path / "errors",
    )
    return StorageService(settings, FileService())


def test_store_crawl_result(storage_service: StorageService) -> None:
    dt = datetime(2026, 6, 14, 10, 15, 0, tzinfo=UTC)
    document = CrawlResultDocument(
        execution_id="testco_20260614_101500",
        company=CompanyInfo(id="testco", name="Test Company"),
        crawler=CrawlerInfo(
            started_at=dt.isoformat(),
            completed_at=dt.isoformat(),
            duration_ms=100,
            status="SUCCESS",
        ),
        statistics=Statistics(total_jobs=1),
        jobs=[
            Job(
                job_id="testco_abc",
                job_title="Engineer",
                job_url="https://example.com/jobs/1",
                raw_data={"department": "Engineering"},
            )
        ],
    )

    path = storage_service.store_crawl_result(document, dt=dt)
    assert path.exists()
    assert path.name == "10-15-00.json"
    assert "14-06-2026" in str(path)
    assert "testco" in str(path)

    data = FileService().read_json(path)
    assert data["statistics"]["total_jobs"] == 1
    assert data["jobs"][0]["raw_data"]["department"] == "Engineering"


def test_store_error(storage_service: StorageService) -> None:
    dt = datetime(2026, 6, 14, 10, 15, 0, tzinfo=UTC)
    error = ErrorRecord(
        execution_id="testco_20260614_101500",
        company="testco",
        timestamp=dt.isoformat(),
        error_type="TimeoutError",
        message="Request timed out",
        stacktrace="Traceback...",
    )

    path = storage_service.store_error(error, dt=dt)
    assert path.exists()
    assert "errors" in str(path)


def test_get_recent_history(storage_service: StorageService) -> None:
    dt = datetime(2026, 6, 14, 10, 15, 0, tzinfo=UTC)
    document = CrawlResultDocument(
        execution_id="testco_20260614_101500",
        company=CompanyInfo(id="testco", name="Test Company"),
        crawler=CrawlerInfo(
            started_at=dt.isoformat(),
            completed_at=dt.isoformat(),
            duration_ms=50,
            status="SUCCESS",
        ),
        statistics=Statistics(total_jobs=2),
        jobs=[],
    )
    storage_service.store_crawl_result(document, dt=dt)

    history = storage_service.get_recent_history("testco", limit=5)
    assert len(history) == 1
    assert history[0].execution_id == "testco_20260614_101500"
    assert history[0].total_jobs == 2
