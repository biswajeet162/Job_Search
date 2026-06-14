from pathlib import Path

import yaml

from app.config.settings import Settings, get_settings
from app.models.company import AppConfig, CompanyConfig, SchedulerConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Loads and validates YAML configuration for companies and scheduler."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._config: AppConfig | None = None

    @property
    def config_path(self) -> Path:
        assert self._settings.config_path is not None
        return self._settings.config_path

    def load(self, force_reload: bool = False) -> AppConfig:
        """Load configuration from YAML file."""
        if self._config is not None and not force_reload:
            return self._config

        logger.info("Loading configuration from %s", self.config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

        scheduler_data = raw.get("scheduler", {})
        companies_data = raw.get("companies", [])

        self._config = AppConfig(
            scheduler=SchedulerConfig(**scheduler_data),
            companies=[CompanyConfig(**item) for item in companies_data],
        )

        logger.info(
            "Configuration loaded: %d companies, max_workers=%d",
            len(self._config.companies),
            self._config.scheduler.max_workers,
        )
        return self._config

    def get_company(self, company_id: str) -> CompanyConfig | None:
        """Return a company configuration by ID."""
        config = self.load()
        for company in config.companies:
            if company.id == company_id:
                return company
        return None

    def get_enabled_companies(self) -> list[CompanyConfig]:
        """Return all enabled company configurations."""
        return [company for company in self.load().companies if company.enabled]
