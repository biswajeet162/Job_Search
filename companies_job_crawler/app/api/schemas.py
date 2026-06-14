from pydantic import BaseModel, Field

from app.models.company import CompanyConfig, SchedulerConfig
from app.models.crawl_result import CrawlExecutionResult, CrawlHistoryEntry


class HealthResponse(BaseModel):
    status: str = Field(examples=["UP"])


class SchedulerStatusResponse(BaseModel):
    running: bool
    last_tick: str | None = None
    tick_interval_seconds: int
    max_workers: int
    enabled_companies: int
    scheduled_jobs: list[dict] = Field(default_factory=list)


class CompaniesResponse(BaseModel):
    companies: list[CompanyConfig]
    scheduler: SchedulerConfig


class CrawlHistoryResponse(BaseModel):
    company_id: str
    count: int
    history: list[CrawlHistoryEntry]


class ErrorResponse(BaseModel):
    detail: str
