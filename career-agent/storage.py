"""Time-based, part-wise storage for raw HTML captures."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_date_folder(dt: datetime) -> str:
    """DD-MM-YYYY — matches companies_job_crawler convention."""
    return dt.strftime("%d-%m-%Y")


def format_time_folder(dt: datetime) -> str:
    """HH-MM-SS run folder name."""
    return dt.strftime("%H-%M-%S")


class HtmlStorage:
    """
    Persists page captures under:

        data/{company_id}/{DD-MM-YYYY}/{HH-MM-SS}/page_001.json
        data/{company_id}/{DD-MM-YYYY}/{HH-MM-SS}/manifest.json
    """

    def __init__(self, base_dir: Path, company_id: str, run_started_at: datetime | None = None) -> None:
        self.base_dir = base_dir
        self.company_id = company_id
        self.run_started_at = run_started_at or utc_now()
        self.run_dir = (
            base_dir
            / company_id
            / format_date_folder(self.run_started_at)
            / format_time_folder(self.run_started_at)
        )
        self.run_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Run directory: %s", self.run_dir)

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    def page_path(self, page_number: int) -> Path:
        return self.run_dir / f"page_{page_number:03d}.json"

    def save_page(self, page_number: int, payload: dict[str, Any]) -> Path:
        path = self.page_path(page_number)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        logger.info("Page %d saved: %s", page_number, path.name)
        return path

    def save_manifest(self, payload: dict[str, Any]) -> Path:
        with self.manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        logger.info("Manifest saved: %s", self.manifest_path)
        return self.manifest_path
