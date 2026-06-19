"""Generic job extraction — behaviour driven entirely by company JSON."""

from __future__ import annotations

from typing import Any

from browser_controller import BrowserController, BrowserControllerError
from company_config import get_job_id_config
from job_id_util import resolve_job_id
from storage import format_scraped_at


class ExtractionError(Exception):
    """Raised when configured extraction cannot complete."""


def extract_raw_jobs(
    browser: BrowserController,
    strategy: dict[str, Any],
    *,
    page_number: int = 1,
) -> list[dict[str, Any]]:
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

    if strategy_type == "fetch_extract":
        return _extract_fetch_jobs(browser, strategy, page_number=page_number)

    raise ExtractionError(f"Unsupported jobLinkStrategy type: {strategy_type}")


def _extract_fetch_jobs(
    browser: BrowserController,
    strategy: dict[str, Any],
    *,
    page_number: int,
) -> list[dict[str, Any]]:
    api_url = strategy["apiUrl"]
    url_template = strategy["urlTemplate"]
    page_size = int(strategy.get("pageSize", 10))
    fields_map = strategy.get("fields", {})
    job_id_config = get_job_id_config(strategy)
    id_field = job_id_config.get("attribute") or strategy.get("jobIdField", "referenceCode")
    id_attribute = job_id_config.get("attribute") or id_field

    data = browser.fetch_json_cached(api_url)
    if not isinstance(data, list):
        raise ExtractionError(f"Expected JSON array from {api_url}")

    start = (page_number - 1) * page_size
    page_items = data[start : start + page_size]
    if not page_items:
        raise ExtractionError(f"No jobs in API page slice {page_number}")

    results: list[dict[str, Any]] = []
    for item in page_items:
        if not isinstance(item, dict):
            continue

        job_id = str(item.get(id_field, "")).strip()
        if not job_id:
            continue

        href = url_template.replace("{jobId}", job_id)
        extracted_fields: dict[str, str] = {}
        for field_name, json_key in fields_map.items():
            extracted_fields[field_name] = str(item.get(json_key, "")).strip()

        title = extracted_fields.get("title", "")
        if not title:
            title_key = fields_map.get("title", "postingTitle")
            title = str(item.get(title_key, "")).strip()

        results.append({
            "href": href,
            "text": title,
            "fields": extracted_fields,
            "attributes": {id_attribute: job_id},
        })

    if not results:
        raise ExtractionError(f"No jobs extracted from API page {page_number}")
    return results


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
    scraped_at = format_scraped_at()

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
        raw_jobs = extract_raw_jobs(browser, strategy, page_number=page_number)
    except BrowserControllerError as exc:
        raise ExtractionError(str(exc)) from exc

    return build_job_records(
        raw_jobs,
        config=config,
        page_number=page_number,
        seen_keys=seen_keys,
    )
