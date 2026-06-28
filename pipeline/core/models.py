"""Pipeline stage and status constants."""

from __future__ import annotations

from enum import Enum


class Stage(str, Enum):
    DISCOVERED = "discovered"
    DETAILS = "details"
    METRICS = "metrics"
    MATCH = "match"
    PUSH = "push"
    COMPLETED = "completed"


class Status(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


# Stage order for job processing
JOB_STAGE_ORDER = [
    Stage.DETAILS,
    Stage.METRICS,
    Stage.MATCH,
    Stage.PUSH,
    Stage.COMPLETED,
]


def next_stage(current: Stage) -> Stage | None:
    if current == Stage.COMPLETED:
        return None
    if current == Stage.DISCOVERED:
        return Stage.DETAILS
    try:
        idx = JOB_STAGE_ORDER.index(current)
        if idx + 1 < len(JOB_STAGE_ORDER):
            return JOB_STAGE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def slugify_company(company: str) -> str:
    import re

    slug = company.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-") or "unknown"


def job_key(company: str, job_id: str) -> str:
    return f"{slugify_company(company)}:{job_id}"
