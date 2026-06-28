"""FastAPI admin dashboard for pipeline monitoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from pipeline.core.config import PipelineConfig
from pipeline.core.models import Stage
from pipeline.core.queue import PipelineQueue

app = FastAPI(title="Job Pipeline Admin", version="1.1.0")
config = PipelineConfig.load()
queue = PipelineQueue(config)

DASHBOARD_HTML = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")


@app.get("/api/stats")
def api_stats():
    return queue.get_stats()


@app.get("/api/jobs")
def api_jobs(
    stage: str | None = None,
    status: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    return queue.db.list_jobs(stage=stage, status=status, limit=limit, offset=offset)


@app.get("/api/ollama/status")
def api_ollama_status():
    import sys

    project3 = str(config.project3_dir)
    if project3 not in sys.path:
        sys.path.insert(0, project3)
    from llm.ollama_client import check_ollama

    status = check_ollama(config.ollama_base_url)
    status["configuredModel"] = config.model_for("job_metrics")
    status["modelAvailable"] = status.get("configuredModel") in status.get("models", [])
    return status


@app.get("/api/jobs/{job_key:path}")
def api_job_detail(job_key: str):
    decoded = unquote(job_key)
    detail = queue.get_job_detail(decoded)
    if not detail:
        raise HTTPException(status_code=404, detail="Job not found")
    return detail


@app.post("/api/retry-failed")
def api_retry_failed(stage: str | None = None):
    stage_enum = Stage(stage) if stage else None
    count = queue.reset_failed_for_retry(stage_enum)
    return {"reset": count}


@app.post("/api/backfill")
def api_backfill():
    count = queue.backfill_from_job_list()
    return {"enqueued": count}


@app.post("/api/demo/seed")
def api_demo_seed():
    """Reset queue and enqueue 3 Cognizant + 2 HCLTech demo jobs."""
    queue.reset_all()
    picked, added = queue.enqueue_demo_jobs({"Cognizant": 3, "HCLTech": 2})
    return {
        "enqueued": added,
        "jobs": [
            {"company": j["company"], "jobId": j["jobId"], "jobTitle": j.get("jobTitle")}
            for j in picked
        ],
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090, reload=False)


if __name__ == "__main__":
    main()
