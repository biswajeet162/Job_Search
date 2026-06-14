import textwrap
from pathlib import Path

import pytest

from app.config.config_loader import ConfigLoader
from app.config.settings import Settings


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    config_file = tmp_path / "companies.yaml"
    config_file.write_text(
        textwrap.dedent(
            """
            scheduler:
              max_workers: 3
              tick_interval_seconds: 60

            companies:
              - id: testco
                name: Test Company
                enabled: true
                interval_minutes: 10
                offset_minutes: 2
                crawler_type: html
                url: https://example.com/careers
            """
        ).strip(),
        encoding="utf-8",
    )
    return config_file


def test_config_loader_loads_companies(temp_config: Path) -> None:
    settings = Settings(
        project_root=temp_config.parent,
        config_path=temp_config,
        storage_dir=temp_config.parent / "storage",
        logs_dir=temp_config.parent / "logs",
        errors_dir=temp_config.parent / "errors",
    )
    loader = ConfigLoader(settings)
    config = loader.load(force_reload=True)

    assert config.scheduler.max_workers == 3
    assert len(config.companies) == 1
    assert config.companies[0].id == "testco"
    assert str(config.companies[0].url) == "https://example.com/careers"


def test_config_loader_get_company(temp_config: Path) -> None:
    settings = Settings(
        project_root=temp_config.parent,
        config_path=temp_config,
    ).resolve_paths()
    loader = ConfigLoader(settings)

    company = loader.get_company("testco")
    assert company is not None
    assert company.name == "Test Company"
    assert loader.get_company("missing") is None


def test_config_loader_enabled_companies(temp_config: Path) -> None:
    settings = Settings(
        project_root=temp_config.parent,
        config_path=temp_config,
    ).resolve_paths()
    loader = ConfigLoader(settings)
    enabled = loader.get_enabled_companies()
    assert len(enabled) == 1
