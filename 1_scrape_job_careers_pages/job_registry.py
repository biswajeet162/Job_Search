"""Track known job IDs and maintain a global new-jobs dashboard."""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from logger_util import log_job_known, log_job_new
from storage import format_scraped_at, slugify

logger = logging.getLogger(__name__)

CONFIDENTIAL_DIR_NAME = "confidential"
DASHBOARD_DIR_NAME = "jobs_dashboard"
CONFIDENTIAL_IDS_FILE = "confidential_job_ids.json"
FINAL_JOB_LIST_FILE = "final_job_list.json"
LOCK_TIMEOUT_SECONDS = 60
LOCK_POLL_SECONDS = 0.1


def job_key(company: str, job_id: str | None, job_url: str | None = None) -> str:
    if job_id:
        return f"{slugify(company)}:{job_id}"
    return f"{slugify(company)}:url:{job_url or ''}"


class FileLockTimeout(TimeoutError):
    """Raised when a cross-process file lock cannot be acquired."""


@contextmanager
def file_lock(lock_path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise FileLockTimeout(f"Could not acquire lock: {lock_path}")
            time.sleep(LOCK_POLL_SECONDS)

    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


class JobRegistry:
    """
    Maintains:
      confidential/confidential_job_ids.json  — known job IDs per company
      jobs_dashboard/final_job_list.json      — aggregated new jobs only
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.confidential_path = base_dir / CONFIDENTIAL_DIR_NAME / CONFIDENTIAL_IDS_FILE
        self.dashboard_path = base_dir / DASHBOARD_DIR_NAME / FINAL_JOB_LIST_FILE
        self.confidential_lock = self.confidential_path.with_suffix(".json.lock")
        self.dashboard_lock = self.dashboard_path.with_suffix(".json.lock")

    def partition_new_jobs(
        self,
        company: str,
        jobs: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        """Return only jobs whose IDs are not yet in the confidential registry."""

        company_slug = slugify(company)
        known_ids = self._load_known_ids_for_company(company_slug)
        new_jobs: list[dict[str, Any]] = []

        for job in jobs:
            job_id = job.get("jobId")
            title = str(job.get("jobTitle", ""))
            id_display = job_id if job_id else "—"

            if not job_id or job_id not in known_ids:
                new_jobs.append(job)
                log_job_new(id_display, title)
            else:
                log_job_known(id_display, title)

        skipped = len(jobs) - len(new_jobs)
        logger.info(
            "Registry filter for %s: %d scraped, %d new, %d already known",
            company_slug,
            len(jobs),
            len(new_jobs),
            skipped,
        )
        return new_jobs, skipped

    def register_new_jobs(self, company: str, new_jobs: list[dict[str, Any]]) -> None:
        if not new_jobs:
            return

        company_slug = slugify(company)
        self._append_confidential_ids(company_slug, new_jobs)
        self._append_dashboard_jobs(new_jobs)
        logger.info(
            "Registry updated: %d new job(s) for %s → %s & %s",
            len(new_jobs),
            company_slug,
            self.confidential_path,
            self.dashboard_path,
        )

    def _load_known_ids_for_company(self, company_slug: str) -> set[str]:
        with file_lock(self.confidential_lock):
            data = self._read_json(self.confidential_path, self._empty_confidential())
        return set(data.get("byCompany", {}).get(company_slug, []))

    def _append_confidential_ids(
        self,
        company_slug: str,
        new_jobs: list[dict[str, Any]],
    ) -> None:
        with file_lock(self.confidential_lock):
            data = self._read_json(self.confidential_path, self._empty_confidential())
            by_company: dict[str, list[str]] = data.setdefault("byCompany", {})
            ids = set(by_company.get(company_slug, []))

            for job in new_jobs:
                job_id = job.get("jobId")
                if job_id:
                    ids.add(str(job_id))

            by_company[company_slug] = sorted(ids)
            data["updatedAt"] = format_scraped_at()
            self._write_json(self.confidential_path, data)

    def _append_dashboard_jobs(self, new_jobs: list[dict[str, Any]]) -> None:
        with file_lock(self.dashboard_lock):
            data = self._read_json(self.dashboard_path, self._empty_dashboard())
            jobs: list[dict[str, Any]] = data.setdefault("jobs", [])
            existing_keys = {
                job_key(
                    job.get("company", ""),
                    job.get("jobId"),
                    job.get("jobUrl"),
                )
                for job in jobs
            }

            added = 0
            for job in new_jobs:
                key = job_key(
                    job.get("company", ""),
                    job.get("jobId"),
                    job.get("jobUrl"),
                )
                if key in existing_keys:
                    continue
                jobs.append(job)
                existing_keys.add(key)
                added += 1

            data["totalJobs"] = len(jobs)
            data["updatedAt"] = format_scraped_at()
            self._write_json(self.dashboard_path, data)
            logger.info("Dashboard appended %d job(s)", added)

    @staticmethod
    def _empty_confidential() -> dict[str, Any]:
        return {"updatedAt": None, "byCompany": {}}

    @staticmethod
    def _empty_dashboard() -> dict[str, Any]:
        return {"updatedAt": None, "totalJobs": 0, "jobs": []}

    @staticmethod
    def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return dict(default)

        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
