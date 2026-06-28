"""Save job metrics JSON files."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-") or "unknown"


def _sanitize_job_id(job_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", job_id.strip())
    return cleaned or "unknown"


class MetricsStorage:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_metrics(
        self,
        *,
        job_id: str,
        company: str,
        source_detail_file: str,
        payload: dict[str, Any],
    ) -> Path:
        payload["sourceDetailFile"] = source_detail_file
        now = datetime.now().astimezone()
        ts = now.strftime("%Y%m%d-%H%M%S")
        filename = f"{_sanitize_job_id(job_id)}-{_slugify(company)}-{ts}-metrics.json"
        path = self.output_dir / filename

        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        return path
