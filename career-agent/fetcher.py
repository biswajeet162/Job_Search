"""Config-driven HTML fetcher — visits hard-coded page URLs and stores raw HTML."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from browser_controller import BrowserController, BrowserControllerError
from storage import HtmlStorage, utc_now

logger = logging.getLogger(__name__)


class FetcherError(Exception):
    """Raised when fetching cannot complete."""


class PageFetcher:
    """
    Loads a company JSON config, visits each listed URL, captures HTML,
    and stores results in time-based part files (one JSON per page).
    """

    def __init__(
        self,
        config_path: Path,
        data_dir: Path,
        browser: BrowserController | None = None,
    ) -> None:
        self.config_path = config_path
        self.data_dir = data_dir
        self.browser = browser or BrowserController(headless=False)
        self.config: dict[str, Any] = {}

    def load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise FetcherError(f"Config not found: {self.config_path}")

        with self.config_path.open(encoding="utf-8") as handle:
            self.config = json.load(handle)

        required = ("companyId", "companyName", "pages")
        missing = [field for field in required if field not in self.config]
        if missing:
            raise FetcherError(f"Config missing required fields: {missing}")

        pages = self.config.get("pages", [])
        if not pages:
            raise FetcherError(f"No pages defined in {self.config_path.name}")

        for index, page in enumerate(pages):
            if "url" not in page:
                raise FetcherError(f"Page entry {index} missing 'url'")
            if "pageNumber" not in page:
                page["pageNumber"] = index + 1

        logger.info(
            "Loaded config: %s (%d pages)",
            self.config["companyName"],
            len(pages),
        )
        return self.config

    def run(self) -> Path:
        """Fetch all configured pages and return the run directory path."""
        self.load_config()

        if not self.config.get("enabled", True):
            raise FetcherError(
                f"Company '{self.config['companyName']}' is disabled in config"
            )

        run_started = utc_now()
        storage = HtmlStorage(
            base_dir=self.data_dir,
            company_id=self.config["companyId"],
            run_started_at=run_started,
        )

        fetch_options = self.config.get("fetchOptions", {})
        pages = sorted(self.config["pages"], key=lambda p: p["pageNumber"])

        manifest: dict[str, Any] = {
            "companyId": self.config["companyId"],
            "companyName": self.config["companyName"],
            "jobPortalName": self.config.get("jobPortalName", self.config["companyName"]),
            "configFile": self.config_path.name,
            "schedule": self.config.get("schedule", {}),
            "runStartedAt": run_started.isoformat(),
            "runCompletedAt": None,
            "totalPages": len(pages),
            "successCount": 0,
            "failureCount": 0,
            "pages": [],
        }

        with self.browser:
            for page_entry in pages:
                page_result = self._fetch_page(page_entry, fetch_options, storage)
                manifest["pages"].append({
                    "pageNumber": page_result["pageNumber"],
                    "url": page_result["url"],
                    "status": page_result["status"],
                    "file": page_result.get("file"),
                    "error": page_result.get("error"),
                })
                if page_result["status"] == "success":
                    manifest["successCount"] += 1
                else:
                    manifest["failureCount"] += 1

        completed = utc_now()
        manifest["runCompletedAt"] = completed.isoformat()
        manifest["durationSeconds"] = round((completed - run_started).total_seconds(), 2)
        storage.save_manifest(manifest)

        logger.info(
            "Fetch completed for %s: %d/%d pages OK → %s",
            self.config["companyName"],
            manifest["successCount"],
            manifest["totalPages"],
            storage.run_dir,
        )
        return storage.run_dir

    def _fetch_page(
        self,
        page_entry: dict[str, Any],
        fetch_options: dict[str, Any],
        storage: HtmlStorage,
    ) -> dict[str, Any]:
        page_number = int(page_entry["pageNumber"])
        url = page_entry["url"]
        scraped_at = datetime.now(timezone.utc).isoformat()

        base_payload: dict[str, Any] = {
            "companyId": self.config["companyId"],
            "companyName": self.config["companyName"],
            "jobPortalName": self.config.get("jobPortalName", self.config["companyName"]),
            "pageNumber": page_number,
            "url": url,
            "scrapedAt": scraped_at,
        }

        try:
            logger.info("Fetching page %d: %s", page_number, url)
            self.browser.open_url(url)

            if fetch_options.get("dismissCookies", True):
                self.browser.dismiss_cookie_banner()

            wait_ms = int(fetch_options.get("waitAfterLoadMs", 3000))
            if wait_ms > 0:
                self.browser.page.wait_for_timeout(wait_ms)

            if fetch_options.get("scrollBeforeCapture", True):
                self.browser.scroll_to_bottom()

            html = self.browser.get_page_html(max_chars=0)  # 0 = no limit
            title = self.browser.page.title()
            final_url = self.browser.page.url

            payload = {
                **base_payload,
                "status": "success",
                "title": title,
                "finalUrl": final_url,
                "htmlLength": len(html),
                "html": html,
            }
            file_path = storage.save_page(page_number, payload)
            return {
                "pageNumber": page_number,
                "url": url,
                "status": "success",
                "file": file_path.name,
            }

        except BrowserControllerError as exc:
            logger.error("Page %d failed: %s", page_number, exc)
            error_payload = {
                **base_payload,
                "status": "error",
                "error": str(exc),
                "html": "",
                "htmlLength": 0,
            }
            storage.save_page(page_number, error_payload)
            return {
                "pageNumber": page_number,
                "url": url,
                "status": "error",
                "file": storage.page_path(page_number).name,
                "error": str(exc),
            }
