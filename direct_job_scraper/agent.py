"""Direct job scraper — extract structured jobs via CSS selectors and pagination."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from browser_controller import BrowserController, BrowserControllerError
from company_config import normalize_config, validate_config
from errors import ScraperError
from extraction import ExtractionError, extract_page_jobs
from logger_util import log_step
from job_registry import JobRegistry
from storage import JobOutputStorage, format_scraped_at, slugify

logger = logging.getLogger(__name__)


class JobScraper:
    """
    Selector-based career page scraper.

    Workflow: steps → filters → scrape N pages → save JSON.
    All behaviour is driven by the company JSON config.
    """

    def __init__(
        self,
        config_path: Path,
        output_dir: Path,
        browser: BrowserController | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.config_path = config_path
        self.output_dir = output_dir
        self.base_dir = base_dir or output_dir.parent
        self.browser = browser or BrowserController(headless=True)
        self.storage = JobOutputStorage(output_dir)
        self.registry = JobRegistry(self.base_dir)
        self.config: dict[str, Any] = {}

    def load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise ScraperError(f"Config not found: {self.config_path}")

        with self.config_path.open(encoding="utf-8") as handle:
            self.config = normalize_config(json.load(handle))

        validate_config(self.config)

        log_step("CONFIG loaded → %s", self.config["companyName"])
        return self.config

    @property
    def scrape_options(self) -> dict[str, Any]:
        return self.config.get("scrapeOptions", {})

    @property
    def max_pages(self) -> int | None:
        value = self.scrape_options.get("maxPages")
        if value is None:
            return None
        return int(value)

    def run(self) -> dict[str, Any]:
        self.load_config()

        if not self.config.get("enabled", True):
            raise ScraperError(f"Company '{self.config['companyName']}' is disabled")

        company = self.config["companyName"]
        all_jobs: list[dict[str, Any]] = []
        page_number = 1
        seen_urls: set[str] = set()

        log_step("BROWSER starting (headless=%s)", self.browser.headless)

        applied_filters = self.config.get("filters", [])

        with self.browser:
            self._execute_steps()
            self._execute_filters()
            self._prepare_for_extract()

            while True:
                if page_number > 1:
                    log_step("PAGINATION navigating to page %d…", page_number)
                    if not self._navigate_to_page(page_number):
                        log_step("PAGINATION stop → could not reach page %d", page_number)
                        break
                    if self.scrape_options.get("scrollBeforeExtract", True):
                        log_step("SCROLL before page %d", page_number)
                        self.browser.scroll_to_bottom()

                log_step("SCRAPE page %d — extracting jobs…", page_number)
                try:
                    page_jobs = extract_page_jobs(
                        self.browser,
                        config=self.config,
                        page_number=page_number,
                        seen_keys=seen_urls,
                    )
                except ExtractionError as exc:
                    raise ScraperError(f"Extraction failed on page {page_number}: {exc}") from exc
                all_jobs.extend(page_jobs)
                log_step(
                    "SCRAPE page %d done → %d jobs (%d total)",
                    page_number,
                    len(page_jobs),
                    len(all_jobs),
                )

                if self.max_pages is not None and page_number >= self.max_pages:
                    log_step("PAGINATION stop → maxPages=%d reached", self.max_pages)
                    break

                pagination = self.config.get("pagination", {})
                pagination_type = pagination.get("type", "next_button")

                if pagination_type == "none":
                    log_step("PAGINATION stop → single page (type=none)")
                    break

                if pagination_type == "next_button":
                    log_step("PAGINATION checking next page…")
                    if not self._has_next_page():
                        log_step("PAGINATION stop → no more pages")
                        break

                page_number += 1

        scraped_at = format_scraped_at()
        log_step("REGISTRY checking %d job(s) against known IDs…", len(all_jobs))
        new_jobs, skipped_known = self.registry.partition_new_jobs(company, all_jobs)
        for job in new_jobs:
            job["scrapedAt"] = scraped_at

        payload = {
            "company": company,
            "careerUrl": self.config["careerUrl"],
            "totalScraped": len(all_jobs),
            "totalJobs": len(new_jobs),
            "newJobs": len(new_jobs),
            "skippedKnownJobs": skipped_known,
            "pagesScraped": page_number,
            "maxPages": self.max_pages,
            "filtersApplied": [
                {"id": f.get("id"), "label": f.get("label"), "value": f.get("value")}
                for f in applied_filters
            ],
            "scrapedAt": scraped_at,
            "jobs": new_jobs,
        }

        log_step(
            "REGISTRY %d scraped → %d new, %d already known",
            len(all_jobs),
            len(new_jobs),
            skipped_known,
        )
        log_step("SAVE writing output JSON…")
        output_path = self.storage.save(company, payload)
        self.registry.register_new_jobs(company, new_jobs)
        log_step("DONE %d new job(s) saved → %s", len(new_jobs), output_path)

        payload["_outputPaths"] = {
            "output": str(output_path),
            "confidentialIds": str(self.registry.confidential_path),
            "jobDashboard": str(self.registry.dashboard_path),
        }
        return payload

    def _execute_steps(self) -> None:
        steps = self.config.get("steps", [])
        career_url = self.config["careerUrl"]
        log_step("STEPS running %d pre-scrape step(s)", len(steps))

        for index, step in enumerate(steps, start=1):
            action = step.get("action", "")
            log_step("STEP [%d/%d] %s", index, len(steps), action)
            try:
                self._run_step(action, step, career_url)
            except BrowserControllerError as exc:
                if action in ("wait_for", "wait"):
                    logger.warning("Optional step '%s' failed, continuing: %s", action, exc)
                    continue
                raise ScraperError(f"Step '{action}' failed: {exc}") from exc

    def _execute_filters(self) -> None:
        filters = self.config.get("filters", [])
        if not filters:
            log_step("FILTERS none configured — skipping")
            return

        log_step("FILTERS applying %d filter(s)", len(filters))
        for index, filter_cfg in enumerate(filters, start=1):
            filter_id = filter_cfg.get("id", filter_cfg.get("label", "filter"))
            value = filter_cfg.get("value", "")
            log_step(
                "FILTER [%d/%d] %s → %s (%s)",
                index,
                len(filters),
                filter_id,
                value,
                filter_cfg.get("action", "fill"),
            )
            optional = filter_cfg.get("optional", False)
            try:
                self._apply_filter(filter_cfg)
                log_step("FILTER [%d/%d] %s ✓ applied", index, len(filters), filter_id)
            except BrowserControllerError as exc:
                if optional:
                    logger.warning("Optional filter '%s' skipped: %s", filter_id, exc)
                    continue
                raise ScraperError(f"Filter '{filter_id}' failed: {exc}") from exc

        wait_ms = int(self.scrape_options.get("waitAfterFiltersMs", 0))
        if wait_ms > 0:
            log_step("WAIT %dms after filters", wait_ms)
            self.browser.wait_ms(wait_ms)

    def _prepare_for_extract(self) -> None:
        if self.scrape_options.get("scrollBeforeExtract", True):
            log_step("SCROLL preparing results view")
            self.browser.scroll_to_bottom()

        wait_selector = self.scrape_options.get("waitForResultsSelector")
        if wait_selector:
            wait_state = self.scrape_options.get("waitForResultsState", "visible")
            log_step("WAIT for results selector: %s (state=%s)", wait_selector, wait_state)
            try:
                self.browser.wait_for_selector(
                    wait_selector,
                    state=wait_state,
                )
            except BrowserControllerError as exc:
                logger.warning("Results selector not found, continuing: %s", exc)

    def _apply_filter(self, filter_cfg: dict[str, Any]) -> None:
        action = filter_cfg.get("action", "fill")
        value = filter_cfg.get("value", "")

        if action == "fill":
            self.browser.fill(filter_cfg["selector"], value)
            if filter_cfg.get("submit", True):
                self.browser.page.keyboard.press("Enter")
                self.browser._wait_for_settle(pause_ms=2000)
            return

        if action == "select":
            self.browser.select_dropdown(
                filter_cfg["selector"],
                value,
                match_by=filter_cfg.get("matchBy", "label"),
            )
            self.browser._wait_for_settle(pause_ms=2000)
            return

        if action == "facet_pick":
            self.browser.apply_facet_filter(
                open_selector=filter_cfg["openSelector"],
                input_selector=filter_cfg["inputSelector"],
                value=value,
                option_selector=filter_cfg["optionSelector"],
                wait_ms=int(filter_cfg.get("waitMs", 1000)),
            )
            return

        if action == "autocomplete":
            self.browser.apply_autocomplete(
                input_selector=filter_cfg["inputSelector"],
                value=value,
                option_selector=filter_cfg.get("optionSelector"),
                option_text=filter_cfg.get("optionText"),
                open_selector=filter_cfg.get("openSelector"),
                wait_ms=int(filter_cfg.get("waitMs", 800)),
            )
            return

        if action == "click_option":
            self.browser.click_option(
                open_selector=filter_cfg["openSelector"],
                option_selector=filter_cfg["optionSelector"],
                wait_ms=int(filter_cfg.get("waitMs", 500)),
            )
            return

        if action == "checkbox":
            self.browser.toggle_facet_checkbox(
                checkbox_selector=filter_cfg["checkboxSelector"],
                open_selector=filter_cfg.get("openSelector"),
                ensure_checked=filter_cfg.get("ensureChecked", True),
            )
            return

        if action == "click":
            self.browser.click(filter_cfg["selector"])
            return

        raise ScraperError(f"Unknown filter action: {action}")

    def _run_step(self, action: str, step: dict[str, Any], career_url: str) -> None:
        if action == "open_url":
            url = step.get("url", career_url)
            log_step("  → open_url: %s", url)
            self.browser.open_url(url)
            return

        if action == "dismiss_cookies":
            log_step("  → dismiss_cookies")
            self.browser.dismiss_page_overlays(step.get("selectors"))
            return

        if action == "dismiss_overlays":
            log_step("  → dismiss_overlays")
            self.browser.dismiss_page_overlays(step.get("selectors"))
            return

        if action == "apply_filter":
            self._apply_filter({**step, "action": step.get("filterAction", "fill")})
            return

        if action == "click":
            self.browser.click(step["selector"])
            return

        if action == "scroll":
            self.browser.scroll_to_bottom()
            return

        if action == "wait_for":
            self.browser.wait_for_selector(step["selector"])
            return

        if action == "wait":
            self.browser.wait_ms(int(step.get("ms", 1000)))
            return

        if action == "screenshot":
            slug = slugify(self.config["companyName"])
            path = str(self.output_dir.parent / "debug" / f"{slug}.png")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.browser.take_screenshot(path)
            return

        logger.warning("Unknown step action ignored: %s", action)

    def _navigate_to_page(self, page_number: int) -> bool:
        pagination = self.config.get("pagination")
        if not pagination:
            return False

        pagination_type = pagination.get("type", "next_button")

        if pagination_type == "page_jump":
            return self.browser.jump_to_page(
                page_number,
                input_selector=pagination["inputSelector"],
                button_selector=pagination["goButtonSelector"],
            )

        if pagination_type == "none":
            return False

        if pagination_type == "next_button":
            return self._go_to_next_page()

        logger.warning("Unsupported pagination type: %s", pagination_type)
        return False

    def _has_next_page(self) -> bool:
        pagination = self.config.get("pagination")
        if not pagination or pagination.get("type") != "next_button":
            return False

        selector = pagination["selector"]
        if not self.browser.selector_exists(selector):
            logger.info("Pagination selector not found; stopping")
            return False
        return True

    def _go_to_next_page(self) -> bool:
        pagination = self.config.get("pagination")
        if not pagination:
            return False

        if pagination.get("type", "next_button") != "next_button":
            return False

        selector = pagination["selector"]
        return self.browser.next_page(selector)
