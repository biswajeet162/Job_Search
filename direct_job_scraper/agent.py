"""Direct job scraper — extract structured jobs via CSS selectors and pagination."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from browser_controller import BrowserController, BrowserControllerError
from job_id_util import extract_job_id
from logger_util import log_job, log_step
from storage import JobOutputStorage, slugify

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Raised when scraping cannot complete."""


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
    ) -> None:
        self.config_path = config_path
        self.output_dir = output_dir
        self.browser = browser or BrowserController(headless=True)
        self.storage = JobOutputStorage(output_dir)
        self.config: dict[str, Any] = {}

    def load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise ScraperError(f"Config not found: {self.config_path}")

        with self.config_path.open(encoding="utf-8") as handle:
            self.config = json.load(handle)

        required = ("companyName", "careerUrl", "jobLinkStrategy")
        missing = [field for field in required if field not in self.config]
        if missing:
            raise ScraperError(f"Config missing required fields: {missing}")

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
        applied_filters = self.config.get("filters", [])

        log_step("BROWSER starting (headless=%s)", self.browser.headless)

        with self.browser:
            self._execute_steps()
            self._execute_filters()
            self._prepare_for_extract()

            while True:
                log_step("SCRAPE page %d — extracting jobs…", page_number)
                page_jobs = self._extract_jobs(page_number, seen_urls)
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

                log_step("PAGINATION checking next page…")
                if not self._go_to_next_page():
                    log_step("PAGINATION stop → no more pages")
                    break

                page_number += 1
                if self.scrape_options.get("scrollBeforeExtract", True):
                    log_step("SCROLL before page %d", page_number)
                    self.browser.scroll_to_bottom()

        scraped_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "company": company,
            "careerUrl": self.config["careerUrl"],
            "totalJobs": len(all_jobs),
            "pagesScraped": page_number,
            "maxPages": self.max_pages,
            "filtersApplied": [
                {"id": f.get("id"), "label": f.get("label"), "value": f.get("value")}
                for f in applied_filters
            ],
            "scrapedAt": scraped_at,
            "jobs": all_jobs,
        }

        log_step("SAVE writing output JSON…")
        latest_path, history_path = self.storage.save(company, payload)
        log_step("DONE %d jobs saved → %s", len(all_jobs), latest_path.name)

        payload["_outputPaths"] = {
            "latest": str(latest_path),
            "history": str(history_path),
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
            log_step("WAIT for results selector: %s", wait_selector)
            try:
                self.browser.wait_for_selector(wait_selector)
            except BrowserControllerError as exc:
                logger.warning("Results selector not found, continuing: %s", exc)

    def _apply_filter(self, filter_cfg: dict[str, Any]) -> None:
        action = filter_cfg.get("action", "fill")
        value = filter_cfg.get("value", "")

        if action == "fill":
            self.browser.fill(filter_cfg["selector"], value)
            if filter_cfg.get("submit", True):
                self.browser.page.keyboard.press("Enter")
                self.browser.page.wait_for_load_state("networkidle")
            return

        if action == "select":
            self.browser.select_dropdown(
                filter_cfg["selector"],
                value,
                match_by=filter_cfg.get("matchBy", "label"),
            )
            self.browser.page.wait_for_load_state("networkidle")
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
            self.browser.dismiss_cookie_banner()
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

    def _extract_jobs(
        self,
        page_number: int,
        seen_urls: set[str],
    ) -> list[dict[str, Any]]:
        strategy = self.config["jobLinkStrategy"]
        strategy_type = strategy.get("type", "direct_extract")
        scraped_at = datetime.now(timezone.utc).isoformat()
        company = self.config["companyName"]

        if strategy_type == "hover_and_extract":
            raw_links = self.browser.extract_hover_links(
                job_card_selector=strategy["jobCardSelector"],
                link_selector=strategy.get("linkSelector", "a"),
            )
        elif strategy_type == "direct_extract":
            selector = strategy.get("linkSelector") or strategy.get("jobCardSelector", "a")
            raw_links = self.browser.extract_links(selector)
        else:
            raise ScraperError(f"Unsupported jobLinkStrategy type: {strategy_type}")

        jobs: list[dict[str, Any]] = []
        for link in raw_links:
            url = link.get("href", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            job_id = extract_job_id(url, strategy)
            title = link.get("text", "").strip()

            jobs.append({
                "company": company,
                "jobId": job_id,
                "jobTitle": title,
                "jobUrl": url,
                "location": self.config.get("defaultLocation", ""),
                "pageNumber": page_number,
                "scrapedAt": scraped_at,
            })

            id_display = job_id if job_id else "—"
            log_job("  JOB [%s] %s", id_display, title[:70])

        return jobs

    def _go_to_next_page(self) -> bool:
        pagination = self.config.get("pagination")
        if not pagination:
            return False

        if pagination.get("type", "next_button") != "next_button":
            logger.warning("Unsupported pagination type: %s", pagination.get("type"))
            return False

        selector = pagination["selector"]
        if not self.browser.selector_exists(selector):
            logger.info("Pagination selector not found; stopping")
            return False

        return self.browser.next_page(selector)
