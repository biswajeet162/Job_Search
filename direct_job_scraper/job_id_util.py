"""Resolve job IDs using per-company rules from JSON config."""

from __future__ import annotations

import re
from typing import Any


def extract_job_id_from_url(url: str, pattern: str) -> str:
    if not url or not pattern:
        return ""
    match = re.search(pattern, url, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def resolve_job_id(
    *,
    url: str,
    raw_record: dict[str, Any],
    job_id_config: dict[str, Any],
) -> str:
    """
    Resolve a job ID using company-specific rules.

    Config shape (in jobLinkStrategy.jobId):
      - source: url | attribute | attribute_first | url_first
      - urlPattern: regex with one capture group
      - attribute: HTML attribute name (e.g. data-job-id)
      - attributeScope: link | card (where attribute is read)
    """

    source = job_id_config.get("source", "url")
    pattern = job_id_config.get("urlPattern", "")
    attribute = job_id_config.get("attribute", "")

    from_url = extract_job_id_from_url(url, pattern) if pattern else ""
    from_attribute = str(raw_record.get("attributes", {}).get(attribute, "")).strip()

    if source == "url":
        return from_url
    if source == "attribute":
        return from_attribute
    if source == "url_first":
        return from_url or from_attribute
    if source == "attribute_first":
        return from_attribute or from_url

    return from_url or from_attribute
