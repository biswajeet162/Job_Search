"""Persist extracted job results to output/."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RUN_FILENAME_PATTERN = re.compile(r"^(\d+)_\d{2}-\d{2}[-:]\d{2}\.json$")


def run_timestamp() -> datetime:
    """Local time for dated folders and run filenames."""

    return datetime.now().astimezone()


def format_scraped_at(dt: datetime | None = None) -> str:
    """Local timezone ISO timestamp for job records and registry files."""

    return (dt or run_timestamp()).isoformat(timespec="seconds")


def format_date_folder(dt: datetime) -> str:
    return dt.strftime("%d_%m_%Y")


def next_run_serial(run_dir: Path) -> int:
    """Next serial for today: 1, 2, 3… based on existing files in the folder."""

    highest = 0
    for path in run_dir.glob("*.json"):
        match = RUN_FILENAME_PATTERN.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def format_run_filename(serial: int, dt: datetime) -> str:
    """
    Build run filename: {serial}_{HH}-{MM}:{SS}.json
    Example: 1_20-23:56.json

    Windows does not allow ':' in filenames — seconds separator uses '-'.
    """

    hour = dt.strftime("%H")
    minute = dt.strftime("%M")
    second = dt.strftime("%S")
    if sys.platform == "win32":
        return f"{serial}_{hour}-{minute}-{second}.json"
    return f"{serial}_{hour}-{minute}:{second}.json"


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


class JobOutputStorage:
    """
    Saves structured job JSON to:

        output/{company_slug}/{DD_MM_YYYY}/{serial}_{HH}-{MM}-{SS}.json
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, company_name: str, payload: dict[str, Any]) -> Path:
        slug = slugify(company_name)
        now = run_timestamp()

        run_dir = self.output_dir / slug / format_date_folder(now)
        run_dir.mkdir(parents=True, exist_ok=True)

        serial = next_run_serial(run_dir)
        run_path = run_dir / format_run_filename(serial, now)

        with run_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        logger.info("Output saved: %s", run_path)
        return run_path
