from pydantic import BaseModel, Field


class CrawlExecutionResult(BaseModel):
    """In-memory result of a crawler run."""

    execution_id: str
    company_id: str
    success: bool
    total_jobs: int = 0
    file_path: str | None = None
    error_message: str | None = None


class ErrorRecord(BaseModel):
    """Error document stored under errors/."""

    execution_id: str
    company: str
    timestamp: str
    error_type: str
    message: str
    stacktrace: str


class CrawlHistoryEntry(BaseModel):
    """Summary entry for crawl history API."""

    execution_id: str
    file_name: str
    file_path: str
    timestamp: str
    status: str = "SUCCESS"
    total_jobs: int | None = None
