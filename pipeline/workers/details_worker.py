"""Project 2 integration — scrape job detail pages."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.core.config import PipelineConfig
from pipeline.core.models import Stage
from pipeline.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


def _ensure_project2_imports(config: PipelineConfig) -> None:
    if str(config.repo_root) not in sys.path:
        sys.path.insert(0, str(config.repo_root))
    project2 = str(config.project2_dir)
    if project2 not in sys.path:
        sys.path.insert(0, project2)


class DetailsWorker(BaseWorker):
    stage = Stage.DETAILS
    name = "details-worker"

    def __init__(
        self,
        config: PipelineConfig | None = None,
        headless: bool = True,
        *,
        instance_id: int = 1,
    ) -> None:
        super().__init__(config, instance_id=instance_id)
        self.headless = headless
        self._browser = None
        _ensure_project2_imports(self.config)

    def _get_browser(self):
        from browser import BrowserController

        if self._browser is None:
            self._browser = BrowserController(headless=self.headless)
            self._browser.start()
        return self._browser

    def stop(self) -> None:
        super().stop()
        if self._browser is not None:
            self._browser.stop()
            self._browser = None

    def process(self, job: dict) -> str | None:
        from extractors import extract_job_details, try_greenhouse_api, try_smartrecruiters_api
        from storage import DetailStorage
        from utils import format_scraped_at

        company = job["company"]
        job_id = job["job_id"]
        job_url = job["job_url"]

        source_job = {
            "company": company,
            "jobId": job_id,
            "jobTitle": job.get("job_title", ""),
            "jobUrl": job_url,
            "location": job.get("location", ""),
        }

        browser = None
        needs_browser = True
        for api_fn in (try_smartrecruiters_api, try_greenhouse_api):
            result = api_fn(job_url)
            if result and (
                result["details"].get("description") or result["details"].get("title")
            ):
                needs_browser = False
                extracted = result
                break
        else:
            extracted = None

        if needs_browser:
            browser = self._get_browser()
            company_config_dir = self.config.project2_dir / "company_configs"
            extracted = extract_job_details(
                job_url=job_url,
                company=company,
                browser=browser,
                company_config_dir=company_config_dir,
            )

        payload: dict[str, Any] = {
            "sourceJob": source_job,
            "sourceUrl": job_url,
            "scrapedAt": format_scraped_at(),
            "extractionMethod": extracted["extractionMethod"],
            "details": extracted["details"],
        }

        storage = DetailStorage(
            self.config.details_dir,
            self.config.project2_dir / "job_details_index.json",
        )
        saved = storage.save_detail(job_id=job_id, company=company, payload=payload)
        return saved.name
