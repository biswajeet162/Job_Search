from fastapi import APIRouter

from app.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns UP when the Job Crawler Engine process is running.",
)
def health_check() -> HealthResponse:
    return HealthResponse(status="UP")
