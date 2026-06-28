"""Persist scraped job detail JSON files and maintain an index."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from utils import build_detail_filename, format_scraped_at

logger = logging.getLogger(__name__)


class DetailStorage:
    def __init__(self, output_dir: Path, index_path: Path) -> None:
        self.output_dir = output_dir
        self.index_path = index_path
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.index: dict[str, Any] = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"updatedAt": None, "totalFiles": 0, "files": []}
        with self.index_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("files", [])
        return data

    def save_detail(
        self,
        *,
        job_id: str,
        company: str,
        payload: dict[str, Any],
        scraped_at: datetime | None = None,
    ) -> Path:
        now = scraped_at or datetime.now().astimezone()
        filename = build_detail_filename(job_id, company, now)
        path = self.output_dir / filename

        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        self.index["files"].append({
            "filename": filename,
            "company": company,
            "jobId": job_id,
            "jobUrl": payload.get("sourceUrl", ""),
            "jobTitle": payload.get("sourceJob", {}).get("jobTitle", ""),
            "extractionMethod": payload.get("extractionMethod", ""),
            "scrapedAt": payload.get("scrapedAt", format_scraped_at(now)),
        })
        self.index["totalFiles"] = len(self.index["files"])
        self.index["updatedAt"] = format_scraped_at()
        self._save_index()

        logger.info("Detail saved: %s", path.name)
        return path

    def _save_index(self) -> None:
        with self.index_path.open("w", encoding="utf-8") as handle:
            json.dump(self.index, handle, indent=2, ensure_ascii=False)
