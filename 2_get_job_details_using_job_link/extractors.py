"""Extract job details from APIs, JSON-LD, and DOM."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from browser import BrowserController
from utils import first_non_empty, strip_html

logger = logging.getLogger(__name__)

GENERIC_TITLE_SELECTORS = [
    "h1",
    "h2.job-title",
    ".job-title",
    ".jobTitle",
    "[data-testid='job-title']",
    ".position-title",
    ".job-header-title",
    "main h1",
]

GENERIC_DESCRIPTION_SELECTORS = [
    ".job-description",
    ".jobDescription",
    "#job-description",
    "[class*='job-description']",
    "[class*='jobDescription']",
    ".job-details",
    ".jobdetail",
    "article",
    "main",
]

GENERIC_META_SELECTORS = [
    ".job-location",
    ".jobLocation",
    "[class*='location']",
    ".job-meta",
    ".employment-type",
]


def _http_get_json(url: str, timeout: int = 30) -> dict[str, Any] | list[Any] | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 JobDetailScraper/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        logger.debug("API fetch failed for %s: %s", url, exc)
        return None


def try_smartrecruiters_api(url: str) -> dict[str, Any] | None:
    match = re.search(
        r"jobs\.smartrecruiters\.com/([^/]+)/(\d+)",
        url,
        re.IGNORECASE,
    )
    if not match:
        return None

    company_slug, posting_id = match.group(1), match.group(2)
    api_url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings/{posting_id}"
    data = _http_get_json(api_url)
    if not isinstance(data, dict):
        return None

    sections = data.get("jobAd", {}).get("sections", {})
    description_html = sections.get("jobDescription", {}).get("text", "")
    qualifications_html = sections.get("qualifications", {}).get("text", "")
    additional_html = sections.get("additionalInformation", {}).get("text", "")

    location = first_non_empty(
        data.get("location", {}).get("fullLocation"),
        ", ".join(
            part for part in [
                data.get("location", {}).get("city"),
                data.get("location", {}).get("region"),
                data.get("location", {}).get("country"),
            ]
            if part
        ),
    )

    return {
        "extractionMethod": "smartrecruiters_api",
        "details": {
            "title": data.get("name", ""),
            "description": strip_html(description_html),
            "descriptionHtml": description_html,
            "qualifications": strip_html(qualifications_html),
            "additionalInformation": strip_html(additional_html),
            "location": location,
            "employmentType": data.get("typeOfEmployment", {}).get("label", ""),
            "department": data.get("department", {}).get("label", ""),
            "postedDate": data.get("releasedDate", ""),
            "companyName": data.get("company", {}).get("name", ""),
            "experienceLevel": data.get("experienceLevel", {}).get("label", ""),
            "industry": data.get("industry", {}).get("label", ""),
            "function": data.get("function", {}).get("label", ""),
            "rawApi": data,
        },
    }


def try_greenhouse_api(url: str) -> dict[str, Any] | None:
    match = re.search(
        r"greenhouse\.io/([^/]+)/jobs/(\d+)",
        url,
        re.IGNORECASE,
    )
    if not match:
        return None

    board, job_id = match.group(1), match.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
    data = _http_get_json(api_url)
    if not isinstance(data, dict):
        return None

    description_html = data.get("content", "")
    return {
        "extractionMethod": "greenhouse_api",
        "details": {
            "title": data.get("title", ""),
            "description": strip_html(description_html),
            "descriptionHtml": description_html,
            "location": data.get("location", {}).get("name", "") if isinstance(data.get("location"), dict) else str(data.get("location", "")),
            "postedDate": data.get("updated_at", ""),
            "department": ", ".join(
                dep.get("name", "") for dep in data.get("departments", []) if isinstance(dep, dict)
            ),
            "employmentType": ", ".join(
                office.get("name", "") for office in data.get("offices", []) if isinstance(office, dict)
            ),
            "rawApi": data,
        },
    }


def _collect_json_ld(page_data: list[Any]) -> list[dict[str, Any]]:
    postings: list[dict[str, Any]] = []
    for item in page_data:
        if not isinstance(item, dict):
            continue
        item_type = item.get("@type")
        if item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type):
            postings.append(item)
        graph = item.get("@graph")
        if isinstance(graph, list):
            for node in graph:
                if isinstance(node, dict) and node.get("@type") == "JobPosting":
                    postings.append(node)
    return postings


def extract_json_ld(browser: BrowserController) -> dict[str, Any] | None:
    raw = browser.evaluate(
        """() => {
            const scripts = [...document.querySelectorAll('script[type="application/ld+json"]')];
            return scripts.map(s => {
                try { return JSON.parse(s.textContent); } catch (e) { return null; }
            }).filter(Boolean);
        }"""
    )
    postings = _collect_json_ld(raw or [])
    if not postings:
        return None

    job = postings[0]
    description = job.get("description", "")
    hiring = job.get("hiringOrganization", {})
    location = job.get("jobLocation", {})
    address = ""
    if isinstance(location, dict):
        addr = location.get("address", {})
        if isinstance(addr, dict):
            address = ", ".join(
                part for part in [
                    addr.get("addressLocality"),
                    addr.get("addressRegion"),
                    addr.get("addressCountry"),
                ]
                if part
            )
    elif isinstance(location, list) and location:
        first = location[0]
        if isinstance(first, dict):
            addr = first.get("address", {})
            if isinstance(addr, dict):
                address = ", ".join(
                    part for part in [
                        addr.get("addressLocality"),
                        addr.get("addressRegion"),
                        addr.get("addressCountry"),
                    ]
                    if part
                )

    return {
        "extractionMethod": "json_ld",
        "details": {
            "title": job.get("title", ""),
            "description": strip_html(description) if "<" in description else description,
            "descriptionHtml": description if "<" in description else "",
            "location": address,
            "employmentType": job.get("employmentType", ""),
            "postedDate": job.get("datePosted", ""),
            "validThrough": job.get("validThrough", ""),
            "companyName": hiring.get("name", "") if isinstance(hiring, dict) else "",
            "identifier": job.get("identifier", ""),
            "rawJsonLd": job,
        },
    }


def extract_with_company_config(
    browser: BrowserController,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    fields = config.get("fields", {})
    title = browser.query_text(fields.get("title", GENERIC_TITLE_SELECTORS), min_length=3)
    description = browser.query_text(
        fields.get("description", GENERIC_DESCRIPTION_SELECTORS),
        min_length=80,
    )
    description_html = browser.query_html(fields.get("description", GENERIC_DESCRIPTION_SELECTORS))

    if not title and not description:
        return None

    location = browser.query_text(fields.get("location", GENERIC_META_SELECTORS), min_length=2)
    employment_type = browser.query_text(fields.get("employmentType", []), min_length=2)

    return {
        "extractionMethod": "company_config",
        "details": {
            "title": title,
            "description": description,
            "descriptionHtml": description_html,
            "location": location,
            "employmentType": employment_type,
            "pageTitle": browser.page_title(),
        },
    }


def extract_generic_dom(browser: BrowserController) -> dict[str, Any]:
    title = browser.query_text(GENERIC_TITLE_SELECTORS, min_length=3)
    description = browser.query_text(GENERIC_DESCRIPTION_SELECTORS, min_length=120)
    description_html = browser.query_html(GENERIC_DESCRIPTION_SELECTORS)
    location = browser.query_text(GENERIC_META_SELECTORS, min_length=2)

    if not title:
        title = browser.page_title()

    return {
        "extractionMethod": "generic_dom",
        "details": {
            "title": title,
            "description": description,
            "descriptionHtml": description_html,
            "location": location,
            "pageTitle": browser.page_title(),
            "finalUrl": browser.current_url(),
        },
    }


def load_company_config(config_dir: Any, company: str) -> dict[str, Any]:
    from pathlib import Path

    from utils import slugify

    config_dir = Path(config_dir)
    compact = re.sub(r"[^a-z0-9]+", "", company.lower())
    candidates = [
        config_dir / f"{slugify(company)}.json",
        config_dir / f"{compact}.json",
    ]
    seen: set[str] = set()
    for path in candidates:
        if path.name in seen:
            continue
        seen.add(path.name)
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
    return {}


def extract_job_details(
    *,
    job_url: str,
    company: str,
    browser: BrowserController | None,
    company_config_dir: Any,
) -> dict[str, Any]:
    for api_fn in (try_smartrecruiters_api, try_greenhouse_api):
        result = api_fn(job_url)
        if result and (
            result["details"].get("description") or result["details"].get("title")
        ):
            return result

    if browser is None:
        raise RuntimeError("Browser required for non-API job URLs")

    config = load_company_config(company_config_dir, company)
    browser.open_url(job_url)
    browser.dismiss_overlays(config.get("cookieSelectors", []))

    wait_selector = config.get("waitForSelector")
    if wait_selector:
        try:
            browser.wait_for_selector(wait_selector)
        except Exception:
            logger.debug("waitForSelector not found: %s", wait_selector)

    extra_wait = int(config.get("extraWaitMs", 0))
    if extra_wait > 0:
        browser.wait_ms(extra_wait)

    result = extract_json_ld(browser)
    if result and (result["details"].get("description") or result["details"].get("title")):
        return result

    if config:
        result = extract_with_company_config(browser, config)
        if result and (result["details"].get("description") or result["details"].get("title")):
            return result

    return extract_generic_dom(browser)
