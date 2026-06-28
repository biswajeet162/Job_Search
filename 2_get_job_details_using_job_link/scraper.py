"""Orchestrate job detail scraping from final_job_list.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from browser import BrowserController
from extractors import extract_job_details, try_greenhouse_api, try_smartrecruiters_api
from logger_util import log_job_new, log_job_skip, log_step
from registry import DetailRegistry
from storage import DetailStorage
from utils import format_scraped_at

logger = logging.getLogger(__name__)

DEFAULT_JOB_LIST = (
    Path(__file__).resolve().parent.parent
    / "1_scrape_job_careers_pages"
    / "jobs_dashboard"
    / "final_job_list.json"
)


def load_job_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Job list not found: {path}")

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("Invalid job list format: 'jobs' must be a list")
    return jobs


def needs_browser(job_url: str) -> bool:
    for api_fn in (try_smartrecruiters_api, try_greenhouse_api):
        result = api_fn(job_url)
        if result and (
            result["details"].get("description") or result["details"].get("title")
        ):
            return False
    return True


class JobDetailScraper:
    def __init__(
        self,
        *,
        base_dir: Path,
        job_list_path: Path,
        headless: bool = True,
    ) -> None:
        self.base_dir = base_dir
        self.job_list_path = job_list_path
        self.headless = headless
        self.output_dir = base_dir / "job_details"
        self.registry = DetailRegistry(base_dir / "scraped_registry.json")
        self.storage = DetailStorage(
            self.output_dir,
            base_dir / "job_details_index.json",
        )
        self.company_config_dir = base_dir / "company_configs"

    def run(
        self,
        *,
        company: str | None = None,
        limit: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        jobs = load_job_list(self.job_list_path)

        if company:
            company_lower = company.lower()
            jobs = [j for j in jobs if j.get("company", "").lower() == company_lower]

        pending: list[dict[str, Any]] = []
        skipped = 0
        for job in jobs:
            job_id = str(job.get("jobId", "")).strip()
            job_company = str(job.get("company", "")).strip()
            if not job_id or not job.get("jobUrl"):
                continue
            if not force and self.registry.is_scraped(job_company, job_id):
                log_job_skip(job_id, job_company, "already scraped")
                skipped += 1
                continue
            pending.append(job)

        if limit is not None:
            pending = pending[:limit]

        log_step(
            "START %d jobs to scrape (total in list: %d, force=%s)",
            len(pending),
            len(jobs),
            force,
        )

        stats = {"scraped": 0, "failed": 0, "skipped": skipped}

        browser: BrowserController | None = None
        browser_jobs = [j for j in pending if needs_browser(j["jobUrl"])]
        if browser_jobs:
            browser = BrowserController(headless=self.headless)
            browser.start()

        try:
            for index, job in enumerate(pending, start=1):
                job_id = str(job["jobId"])
                job_company = str(job["company"])
                job_url = str(job["jobUrl"])
                job_title = str(job.get("jobTitle", ""))

                log_step(
                    "[%d/%d] %s | %s | %s",
                    index,
                    len(pending),
                    job_company,
                    job_id,
                    job_title[:50],
                )

                try:
                    extracted = extract_job_details(
                        job_url=job_url,
                        company=job_company,
                        browser=browser,
                        company_config_dir=self.company_config_dir,
                    )
                    payload = {
                        "sourceJob": job,
                        "sourceUrl": job_url,
                        "scrapedAt": format_scraped_at(),
                        "extractionMethod": extracted["extractionMethod"],
                        "details": extracted["details"],
                    }
                    saved_path = self.storage.save_detail(
                        job_id=job_id,
                        company=job_company,
                        payload=payload,
                    )
                    self.registry.mark_scraped(
                        job_company,
                        job_id,
                        filename=saved_path.name,
                        job_url=job_url,
                        extraction_method=extracted["extractionMethod"],
                    )
                    self.registry.save()
                    log_job_new(job_id, job_company, extracted["extractionMethod"])
                    stats["scraped"] += 1
                except Exception as exc:
                    logger.error(
                        "Failed [%s | %s]: %s",
                        job_id,
                        job_company,
                        exc,
                        exc_info=logger.isEnabledFor(logging.DEBUG),
                    )
                    stats["failed"] += 1
        finally:
            if browser is not None:
                browser.stop()

        log_step(
            "DONE scraped=%d failed=%d skipped=%d",
            stats["scraped"],
            stats["failed"],
            stats["skipped"],
        )
        return stats
