"""Track which job detail files have already been scraped."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from utils import format_scraped_at, registry_key

logger = logging.getLogger(__name__)


class DetailRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = {
            "updatedAt": None,
            "totalScraped": 0,
            "entries": {},
        }
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            self.data.update(loaded)
            self.data.setdefault("entries", {})

    def is_scraped(self, company: str, job_id: str) -> bool:
        return registry_key(company, job_id) in self.data["entries"]

    def get_entry(self, company: str, job_id: str) -> dict[str, Any] | None:
        return self.data["entries"].get(registry_key(company, job_id))

    def mark_scraped(
        self,
        company: str,
        job_id: str,
        *,
        filename: str,
        job_url: str,
        extraction_method: str,
    ) -> None:
        key = registry_key(company, job_id)
        self.data["entries"][key] = {
            "company": company,
            "jobId": job_id,
            "jobUrl": job_url,
            "filename": filename,
            "extractionMethod": extraction_method,
            "scrapedAt": format_scraped_at(),
        }
        self.data["totalScraped"] = len(self.data["entries"])
        self.data["updatedAt"] = format_scraped_at()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, ensure_ascii=False)
        logger.debug("Registry saved: %s", self.path)
