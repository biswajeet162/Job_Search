"""Generic job extraction — behaviour driven entirely by company JSON."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from browser_controller import BrowserController, BrowserControllerError
from company_config import get_job_id_config
from job_id_util import resolve_job_id
from logger_util import log_job


class ExtractionError(Exception):
    """Raised when configured extraction cannot complete."""


def extract_raw_jobs(browser: BrowserController, strategy: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the configured extraction strategy and return raw page records."""

    strategy_type = strategy.get("type", "direct_extract")

    if strategy_type == "hover_and_extract":
        return browser.extract_hover_links(
            job_card_selector=strategy["jobCardSelector"],
            link_selector=strategy.get("linkSelector", "a"),
        )

    if strategy_type == "direct_extract":
        selector = strategy.get("linkSelector") or strategy.get("jobCardSelector", "a")
        return browser.extract_links(selector)

    if strategy_type == "card_extract":
        fields = strategy.get("fields", {})
        job_id = get_job_id_config(strategy)
        attributes = {}
        if job_id.get("attribute"):
            attributes["jobId"] = job_id["attribute"]

        return browser.extract_structured_cards(
            card_selector=strategy["cardSelector"],
            link_selector=strategy["linkSelector"],
            fields=fields,
            attributes=attributes,
            attribute_scope=job_id.get("attributeScope", "link"),
        )

    raise ExtractionError(f"Unsupported jobLinkStrategy type: {strategy_type}")


def build_job_records(
    raw_jobs: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    page_number: int,
    seen_keys: set[str],
) -> list[dict[str, Any]]:
    """Normalize raw extraction output into output JSON job objects."""

    strategy = config["jobLinkStrategy"]
    job_id_config = get_job_id_config(strategy)
    fields = strategy.get("fields", {})
    company = config["companyName"]
    default_location = config.get("defaultLocation", "")
    scraped_at = datetime.now(timezone.utc).isoformat()

    jobs: list[dict[str, Any]] = []

    for raw in raw_jobs:
        url = str(raw.get("href", "")).strip()
        if not url:
            continue

        job_id = resolve_job_id(url=url, raw_record=raw, job_id_config=job_id_config)
        dedupe_key = job_id or url
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        title = (
            str(raw.get("fields", {}).get("title", "")).strip()
            or str(raw.get("text", "")).strip()
        )
        location = str(raw.get("fields", {}).get("location", "")).strip()
        if not location:
            location = default_location

        job: dict[str, Any] = {
            "company": company,
            "jobId": job_id,
            "jobTitle": title,
            "jobUrl": url,
            "location": location,
            "pageNumber": page_number,
            "scrapedAt": scraped_at,
        }

        for field_name in fields:
            if field_name in {"location", "title"}:
                continue
            value = str(raw.get("fields", {}).get(field_name, "")).strip()
            if value:
                job[field_name] = value

        jobs.append(job)
        id_display = job_id if job_id else "—"
        log_job("  JOB [%s] %s", id_display, title[:70])

    return jobs


def extract_page_jobs(
    browser: BrowserController,
    *,
    config: dict[str, Any],
    page_number: int,
    seen_keys: set[str],
) -> list[dict[str, Any]]:
    """Extract and normalize jobs for one results page."""

    strategy = config["jobLinkStrategy"]
    try:
        raw_jobs = extract_raw_jobs(browser, strategy)
    except BrowserControllerError as exc:
        raise ExtractionError(str(exc)) from exc

    return build_job_records(
        raw_jobs,
        config=config,
        page_number=page_number,
        seen_keys=seen_keys,
    )
