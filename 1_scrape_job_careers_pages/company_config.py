"""Load, normalize, and validate per-company scraper configuration."""

from __future__ import annotations

from typing import Any

from errors import ScraperError

FILTER_ACTIONS = frozenset({
    "fill",
    "select",
    "facet_pick",
    "autocomplete",
    "click_option",
    "checkbox",
    "click",
})

STEP_ACTIONS = frozenset({
    "open_url",
    "dismiss_cookies",
    "dismiss_overlays",
    "apply_filter",
    "click",
    "scroll",
    "wait_for",
    "wait",
    "screenshot",
})

JOB_LINK_STRATEGIES = frozenset({
    "direct_extract",
    "card_extract",
    "hover_and_extract",
    "fetch_extract",
})

PAGINATION_TYPES = frozenset({
    "next_button",
    "page_jump",
    "api_page",
    "infinite_scroll",
    "url_page",
    "none",
})

JOB_ID_SOURCES = frozenset({
    "url",
    "attribute",
    "attribute_first",
    "url_first",
})

STRATEGY_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "direct_extract": ("linkSelector",),
    "card_extract": ("cardSelector", "linkSelector"),
    "hover_and_extract": ("jobCardSelector",),
    "fetch_extract": (),
}

PAGINATION_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "next_button": ("selector",),
    "page_jump": ("inputSelector", "goButtonSelector"),
    "api_page": (),
    "infinite_scroll": (),
    "url_page": ("urlTemplate",),
    "none": (),
}

FILTER_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "fill": ("selector",),
    "select": ("selector",),
    "facet_pick": ("openSelector", "inputSelector", "optionSelector"),
    "autocomplete": ("inputSelector",),
    "click_option": ("openSelector", "optionSelector"),
    "checkbox": ("checkboxSelector",),
    "click": ("selector",),
}


def normalize_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Merge legacy keys into the current schema shape."""

    config = dict(raw)
    strategy = dict(config.get("jobLinkStrategy", {}))

    job_id = dict(strategy.get("jobId", {}))

    legacy_pattern = strategy.pop("jobIdPattern", None) or strategy.pop("jobIdRegex", None)
    if legacy_pattern and not job_id.get("urlPattern"):
        job_id["urlPattern"] = legacy_pattern

    legacy_attribute = strategy.pop("jobIdAttribute", None)
    if legacy_attribute and not job_id.get("attribute"):
        job_id["attribute"] = legacy_attribute

    if job_id:
        strategy["jobId"] = job_id

    fields = dict(strategy.get("fields", {}))
    legacy_location = strategy.pop("locationSelector", None)
    if legacy_location and "location" not in fields:
        fields["location"] = legacy_location
    if fields:
        strategy["fields"] = fields

    config["jobLinkStrategy"] = strategy
    return config


def get_job_id_config(strategy: dict[str, Any]) -> dict[str, Any]:
    """Return normalized job ID rules for a company strategy."""

    job_id = dict(strategy.get("jobId", {}))
    strategy_type = strategy.get("type", "direct_extract")

    if not job_id.get("source"):
        if strategy_type == "card_extract" and job_id.get("attribute"):
            job_id["source"] = "attribute_first"
        elif job_id.get("attribute"):
            job_id["source"] = "attribute_first"
        else:
            job_id["source"] = "url"

    if not job_id.get("attributeScope"):
        job_id["attributeScope"] = "link"

    return job_id


def validate_config(config: dict[str, Any]) -> None:
    """Ensure a company JSON has everything the generic engine needs."""

    required_root = ("companyName", "careerUrl", "jobLinkStrategy")
    missing_root = [field for field in required_root if field not in config]
    if missing_root:
        raise ScraperError(f"Config missing required fields: {missing_root}")

    strategy = config["jobLinkStrategy"]
    strategy_type = strategy.get("type", "direct_extract")
    if strategy_type not in JOB_LINK_STRATEGIES:
        raise ScraperError(
            f"Unsupported jobLinkStrategy.type '{strategy_type}'. "
            f"Use one of: {sorted(JOB_LINK_STRATEGIES)}"
        )

    for field in STRATEGY_REQUIRED_FIELDS[strategy_type]:
        if not strategy.get(field):
            raise ScraperError(
                f"jobLinkStrategy.type '{strategy_type}' requires '{field}'"
            )

    if strategy_type == "fetch_extract":
        if not strategy.get("apiUrl") and not strategy.get("apiUrlTemplate"):
            raise ScraperError(
                "jobLinkStrategy.type 'fetch_extract' requires 'apiUrl' or 'apiUrlTemplate'"
            )
        if not strategy.get("urlTemplate") and not strategy.get("urlField"):
            raise ScraperError(
                "jobLinkStrategy.type 'fetch_extract' requires 'urlTemplate' or 'urlField'"
            )

    job_id = get_job_id_config(strategy)
    if job_id["source"] in {"url", "url_first", "attribute_first"} and not job_id.get("urlPattern"):
        if job_id["source"] == "url":
            raise ScraperError(
                "jobLinkStrategy.jobId.urlPattern is required when source is 'url'"
            )
    if job_id["source"] in {"attribute", "attribute_first", "url_first"} and not job_id.get("attribute"):
        if job_id["source"] == "attribute":
            raise ScraperError(
                "jobLinkStrategy.jobId.attribute is required when source is 'attribute'"
            )

    pagination = config.get("pagination")
    if pagination:
        pagination_type = pagination.get("type", "next_button")
        if pagination_type not in PAGINATION_TYPES:
            raise ScraperError(
                f"Unsupported pagination.type '{pagination_type}'. "
                f"Use one of: {sorted(PAGINATION_TYPES)}"
            )
        for field in PAGINATION_REQUIRED_FIELDS[pagination_type]:
            if not pagination.get(field):
                raise ScraperError(
                    f"pagination.type '{pagination_type}' requires '{field}'"
                )

    for index, step in enumerate(config.get("steps", []), start=1):
        action = step.get("action", "")
        if action and action not in STEP_ACTIONS:
            raise ScraperError(f"Unknown step action at index {index}: {action}")

    for index, filter_cfg in enumerate(config.get("filters", []), start=1):
        action = filter_cfg.get("action", "fill")
        if action not in FILTER_ACTIONS:
            raise ScraperError(f"Unknown filter action at index {index}: {action}")
        for field in FILTER_REQUIRED_FIELDS.get(action, ()):
            if not filter_cfg.get(field):
                raise ScraperError(
                    f"Filter '{filter_cfg.get('id', index)}' action '{action}' "
                    f"requires '{field}'"
                )
