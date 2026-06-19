"""Extract job IDs from URLs using config patterns or common defaults."""

from __future__ import annotations

import re
from typing import Any

# Tried in order when no custom pattern is configured
DEFAULT_JOB_ID_PATTERNS = [
    r"/job/(R-\d+)/",           # Mastercard / Phenom
    r"/job/(\d+)/",             # numeric requisition
    r"[?&]jobId=(\w+)",
    r"[?&]requisitionId=(\w+)",
    r"/requisition/(\d+)",
    r"/jobs/(\d+)",
    r"/job/([A-Z0-9-]+)/",
]


def extract_job_id(url: str, strategy: dict[str, Any] | None = None) -> str:
    """Return job ID from URL, or empty string if not found."""
    if not url:
        return ""

    strategy = strategy or {}
    custom = strategy.get("jobIdPattern") or strategy.get("jobIdRegex")
    patterns: list[str] = [custom] if custom else []
    patterns.extend(DEFAULT_JOB_ID_PATTERNS)

    for pattern in patterns:
        if not pattern:
            continue
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""
