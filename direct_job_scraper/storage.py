"""Persist extracted job results to output/."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_date_folder(dt: datetime) -> str:
    return dt.strftime("%d-%m-%Y")


def format_time_folder(dt: datetime) -> str:
    return dt.strftime("%H-%M-%S")


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


class JobOutputStorage:
    """
    Saves structured job JSON to:

        output/{company_slug}_jobs.json          ← latest snapshot
        output/{company_slug}/{DD-MM-YYYY}/{HH-MM-SS}.json  ← run history
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, company_name: str, payload: dict[str, Any]) -> tuple[Path, Path]:
        slug = slugify(company_name)
        now = utc_now()

        latest_path = self.output_dir / f"{slug}_jobs.json"
        with latest_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        history_dir = self.output_dir / slug / format_date_folder(now)
        history_dir.mkdir(parents=True, exist_ok=True)
        history_path = history_dir / f"{format_time_folder(now)}.json"
        with history_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        logger.info("Latest saved: %s", latest_path)
        logger.info("History saved: %s", history_path)
        return latest_path, history_path
