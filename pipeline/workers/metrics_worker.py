"""Project 3 integration — extract job metrics via local LLM."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from pipeline.core.config import PipelineConfig
from pipeline.core.models import Stage
from pipeline.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


def _ensure_project3_imports(config: PipelineConfig) -> None:
    project3 = str(config.project3_dir)
    if project3 not in sys.path:
        sys.path.insert(0, project3)


class MetricsWorker(BaseWorker):
    stage = Stage.METRICS
    name = "metrics-worker"

    def __init__(
        self,
        config: PipelineConfig | None = None,
        *,
        instance_id: int = 1,
    ) -> None:
        super().__init__(config, instance_id=instance_id)
        _ensure_project3_imports(self.config)

    def process(self, job: dict) -> str | None:
        from job_metrics_extractor import extract_job_metrics
        from metrics_storage import MetricsStorage

        detail_file = job.get("detail_file")
        if not detail_file:
            raise FileNotFoundError(f"No detail_file for job {job['job_key']}")

        detail_path = self.config.details_dir / detail_file
        if not detail_path.exists():
            raise FileNotFoundError(f"Detail file missing: {detail_path}")

        with detail_path.open(encoding="utf-8") as handle:
            detail_data = json.load(handle)

        title = detail_data.get("details", {}).get("title") or job.get("job_title", "")
        logger.info(
            "[%s] OLLAMA extracting metrics for %s | %s",
            self.name,
            job.get("job_id"),
            title[:50],
        )

        metrics_payload = extract_job_metrics(
            detail_data,
            ollama_base_url=self.config.ollama_base_url,
            ollama_model=self.config.model_for("job_metrics"),
        )

        storage = MetricsStorage(self.config.job_metrics_dir)
        saved = storage.save_metrics(
            job_id=job["job_id"],
            company=job["company"],
            source_detail_file=detail_file,
            payload=metrics_payload,
        )
        method = metrics_payload.get("extractionMethod", "?")
        skill_count = len(metrics_payload.get("metrics", {}).get("skills", []))
        logger.info(
            "[%s] METRICS saved via %s — %d skills — %s",
            self.name,
            method,
            skill_count,
            saved.name,
        )
        return saved.name
