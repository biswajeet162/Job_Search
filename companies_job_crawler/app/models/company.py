from pydantic import BaseModel, Field, HttpUrl


class CompanyConfig(BaseModel):
    """Configuration for a single company crawler."""

    id: str
    name: str
    enabled: bool = True
    interval_minutes: int = Field(default=15, ge=1)
    offset_minutes: int = Field(default=0, ge=0)
    crawler_type: str = "html"
    url: HttpUrl
    extra: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class SchedulerConfig(BaseModel):
    """Global scheduler settings."""

    max_workers: int = Field(default=5, ge=1)
    tick_interval_seconds: int = Field(default=60, ge=1)


class AppConfig(BaseModel):
    """Root application configuration."""

    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    companies: list[CompanyConfig] = Field(default_factory=list)
