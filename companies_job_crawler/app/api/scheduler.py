from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import (
    CompaniesResponse,
    CrawlHistoryResponse,
    ErrorResponse,
    SchedulerStatusResponse,
)
from app.dependencies import get_container
from app.models.crawl_result import CrawlExecutionResult

router = APIRouter(tags=["Crawler & Scheduler"])


@router.get(
    "/scheduler/status",
    response_model=SchedulerStatusResponse,
    summary="Scheduler status",
    description="Returns whether the background scheduler is running, last tick time, and worker configuration.",
)
def scheduler_status() -> SchedulerStatusResponse:
    container = get_container()
    status = container.scheduler_service.get_status()
    return SchedulerStatusResponse(**status)


@router.get(
    "/companies",
    response_model=CompaniesResponse,
    summary="List configured companies",
    description="Returns all companies loaded from config/companies.yaml and global scheduler settings.",
)
def list_companies() -> CompaniesResponse:
    container = get_container()
    config = container.config_loader.load()
    return CompaniesResponse(companies=config.companies, scheduler=config.scheduler)


@router.post(
    "/crawler/{company_id}",
    response_model=CrawlExecutionResult,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Trigger manual crawl",
    description=(
        "Immediately runs the company-specific crawl service for the given company ID. "
        "Each company uses its own fetcher, parser, and field mapper."
    ),
)
def trigger_crawl(company_id: str) -> CrawlExecutionResult:
    container = get_container()
    company = container.config_loader.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")

    result = container.crawl_service.trigger_manual_crawl(company_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Crawl failed to start")

    return result


@router.get(
    "/history/{company_id}",
    response_model=CrawlHistoryResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Crawl execution history",
    description="Returns recent stored crawl JSON files for a company, newest first.",
)
def crawl_history(
    company_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum history entries to return"),
) -> CrawlHistoryResponse:
    container = get_container()
    company = container.config_loader.get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found")

    history = container.storage_service.get_recent_history(company_id, limit=limit)
    return CrawlHistoryResponse(company_id=company_id, count=len(history), history=history)
