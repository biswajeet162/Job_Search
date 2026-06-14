from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime paths and environment settings."""

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    config_path: Path | None = None
    storage_dir: Path | None = None
    logs_dir: Path | None = None
    errors_dir: Path | None = None
    log_level: str = "INFO"
    crawler_version: str = "1.0"
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 2.0

    def resolve_paths(self) -> "Settings":
        """Resolve relative paths against project root."""
        root = self.project_root
        if self.config_path is None:
            self.config_path = root / "config" / "companies.yaml"
        if self.storage_dir is None:
            self.storage_dir = root / "storage"
        if self.logs_dir is None:
            self.logs_dir = root / "logs"
        if self.errors_dir is None:
            self.errors_dir = root / "errors"
        return self


def get_settings() -> Settings:
    """Return application settings with resolved paths."""
    return Settings().resolve_paths()
