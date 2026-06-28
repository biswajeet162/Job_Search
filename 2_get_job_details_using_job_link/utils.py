"""Shared helpers for filenames, slugs, and timestamps."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from typing import Any


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-") or "unknown"


def sanitize_job_id(job_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", job_id.strip())
    return cleaned or "unknown"


def format_timestamp(dt: datetime | None = None) -> str:
    value = dt or datetime.now().astimezone()
    if sys.platform == "win32":
        return value.strftime("%Y%m%d-%H%M%S")
    return value.strftime("%Y%m%d-%H%M%S")


def format_scraped_at(dt: datetime | None = None) -> str:
    return (dt or datetime.now().astimezone()).isoformat(timespec="seconds")


def build_detail_filename(job_id: str, company: str, dt: datetime | None = None) -> str:
    return f"{sanitize_job_id(job_id)}-{slugify(company)}-{format_timestamp(dt)}.json"


def registry_key(company: str, job_id: str) -> str:
    return f"{slugify(company)}:{sanitize_job_id(job_id)}"


def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""
