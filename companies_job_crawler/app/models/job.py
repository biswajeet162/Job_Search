from typing import Any

from pydantic import BaseModel, Field


class Job(BaseModel):
    """Standardized job record with preserved raw payload."""

    job_id: str
    job_title: str
    job_url: str
    raw_data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class CompanyInfo(BaseModel):
    id: str
    name: str


class CrawlerInfo(BaseModel):
    started_at: str
    completed_at: str
    duration_ms: int
    status: str
    version: str = "1.0"


class Statistics(BaseModel):
    total_jobs: int = 0


class CrawlResultDocument(BaseModel):
    """Full crawl execution document stored as JSON."""

    execution_id: str
    company: CompanyInfo
    crawler: CrawlerInfo
    statistics: Statistics
    jobs: list[Job] = Field(default_factory=list)

    model_config = {"extra": "allow"}
