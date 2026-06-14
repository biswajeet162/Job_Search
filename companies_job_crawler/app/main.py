from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app import __version__
from app.api.health import router as health_router
from app.api.scheduler import router as scheduler_router
from app.dependencies import get_container
from app.utils.logger import setup_logging

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Service liveness and uptime checks.",
    },
    {
        "name": "Crawler & Scheduler",
        "description": (
            "Scheduler control, company configuration, manual crawls, and history. "
            "Each company uses a dedicated crawl service with its own fetcher, parser, "
            "and field mapper for site-specific job data structures."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = get_container()
    setup_logging(container.settings.logs_dir, container.settings.log_level)
    container.scheduler_service.start()
    yield
    container.scheduler_service.stop()


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=OPENAPI_TAGS,
    )
    schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/icon-white.svg",
    }
    app.openapi_schema = schema
    return app.openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        title="Job Crawler Engine",
        description=(
            "Production-grade modular job crawler for continuous career page monitoring.\n\n"
            "## Architecture\n"
            "Each company has a **dedicated crawl service** with three pluggable components:\n"
            "- **Fetcher** — how raw data is retrieved (HTTP, Playwright, API)\n"
            "- **Parser** — extracts jobs using the site's native field names "
            "(jobId, work_id, job_description, etc.)\n"
            "- **Mapper** — normalizes to `job_id`, `job_title`, `job_url` while preserving "
            "the full native record in `raw_data`\n\n"
            "## Swagger UI\n"
            "Interactive API docs: **/docs** | ReDoc: **/redoc** | OpenAPI JSON: **/openapi.json**"
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        contact={
            "name": "Job Intelligence Platform",
        },
        license_info={
            "name": "Internal Use",
        },
    )

    app.include_router(health_router)
    app.include_router(scheduler_router)
    app.openapi = lambda: custom_openapi(app)

    return app


app = create_app()
