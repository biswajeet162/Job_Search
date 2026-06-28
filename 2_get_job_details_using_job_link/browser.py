"""Playwright browser wrapper for job detail pages."""

from __future__ import annotations

import logging
import time
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

logger = logging.getLogger(__name__)


class BrowserControllerError(Exception):
    pass


class BrowserController:
    DEFAULT_TIMEOUT_MS = 45_000
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY_SEC = 2.0

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        max_retries: int = DEFAULT_RETRIES,
        retry_delay_sec: float = DEFAULT_RETRY_DELAY_SEC,
    ) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise BrowserControllerError("Browser not started")
        return self._page

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._context = self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
        )
        self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)

    def stop(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def __enter__(self) -> BrowserController:
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def _retry(self, action_name: str, fn: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                logger.warning("%s failed (%d/%d): %s", action_name, attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_sec * attempt)
        raise BrowserControllerError(
            f"{action_name} failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def _wait_for_settle(self, pause_ms: int = 2000) -> None:
        try:
            self.page.wait_for_load_state("networkidle", timeout=12_000)
        except Exception:
            pass
        if pause_ms > 0:
            self.page.wait_for_timeout(pause_ms)

    def open_url(self, url: str) -> None:
        def _navigate() -> None:
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self._wait_for_settle()

        self._retry(f"open_url({url})", _navigate)

    def dismiss_overlays(self, extra_selectors: list[str] | None = None) -> None:
        selectors = [
            "#onetrust-accept-btn-handler",
            "button#onetrust-accept-btn-handler",
            "button:has-text('Accept All Cookies')",
            "button:has-text('Accept All')",
            "button:has-text('Accept')",
            "button:has-text('I Accept')",
            "[data-testid='cookie-accept']",
        ]
        if extra_selectors:
            selectors = extra_selectors + selectors

        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.count() == 0 or not locator.is_visible():
                    continue
                locator.click(timeout=2000)
                self.page.wait_for_timeout(600)
            except Exception:
                continue

        try:
            role_btn = self.page.get_by_role("button", name="Accept All Cookies")
            if role_btn.count():
                role_btn.last.click(timeout=2000)
                self.page.wait_for_timeout(600)
        except Exception:
            pass

    def wait_for_selector(self, selector: str, timeout_ms: int | None = None) -> None:
        def _wait() -> None:
            self.page.locator(selector).first.wait_for(
                state="visible",
                timeout=timeout_ms or self.timeout_ms,
            )

        self._retry(f"wait_for_selector({selector})", _wait)

    def wait_ms(self, ms: int) -> None:
        self.page.wait_for_timeout(ms)

    def evaluate(self, script: str, arg: Any = None) -> Any:
        if arg is None:
            return self.page.evaluate(script)
        return self.page.evaluate(script, arg)

    def query_text(self, selectors: list[str], min_length: int = 1) -> str:
        for selector in selectors:
            locator = self.page.locator(selector).first
            if locator.count() == 0:
                continue
            text = locator.inner_text().strip()
            if len(text) >= min_length and "internet explorer" not in text.lower():
                return text
        return ""

    def query_html(self, selectors: list[str]) -> str:
        for selector in selectors:
            locator = self.page.locator(selector).first
            if locator.count() == 0:
                continue
            html = locator.inner_html().strip()
            if html:
                return html
        return ""

    def page_title(self) -> str:
        return self.page.title()

    def current_url(self) -> str:
        return self.page.url
