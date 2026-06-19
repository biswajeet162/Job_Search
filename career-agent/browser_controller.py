"""Playwright browser abstraction with retry handling for career page automation."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

logger = logging.getLogger(__name__)


class BrowserControllerError(Exception):
    """Raised when a browser operation fails after all retries."""


class BrowserController:
    """
    Thin Playwright wrapper that executes deterministic browser actions.

    All career-page interactions go through this layer; the LLM never drives
    the browser directly.
    """

    DEFAULT_TIMEOUT_MS = 30_000
    DEFAULT_RETRIES = 3
    DEFAULT_RETRY_DELAY_SEC = 2.0

    def __init__(
        self,
        headless: bool = False,
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
        self._current_url: str = ""

    @property
    def page(self) -> Page:
        if self._page is None:
            raise BrowserControllerError("Browser not started. Call start() first.")
        return self._page

    def start(self) -> None:
        """Launch Chromium in visible mode and open a fresh page."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)
        logger.info("Browser started (headless=%s)", self.headless)

    def stop(self) -> None:
        """Close browser resources."""
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
        logger.info("Browser stopped")

    def __enter__(self) -> BrowserController:
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def _retry(self, action_name: str, fn: Any) -> Any:
        """Execute *fn* with retries for transient network/DOM failures."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "%s failed (attempt %d/%d): %s",
                    action_name,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_sec * attempt)
        raise BrowserControllerError(
            f"{action_name} failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    def open_url(self, url: str) -> None:
        """Navigate to *url* and wait for the DOM to be ready."""

        def _navigate() -> None:
            self.page.goto(url, wait_until="domcontentloaded")
            self.page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
            self._current_url = url

        self._retry(f"open_url({url})", _navigate)
        logger.info("Page opened: %s", url)

    def dismiss_cookie_banner(self) -> None:
        """Dismiss common cookie consent overlays that block clicks."""
        selectors = [
            "#onetrust-accept-btn-handler",
            "button#onetrust-accept-btn-handler",
            "button:has-text('Accept All Cookies')",
            "button:has-text('Accept All')",
            "button:has-text('Accept')",
            "button:has-text('I Accept')",
            "[data-testid='cookie-accept']",
        ]
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if locator.count() == 0 or not locator.is_visible():
                    continue
                locator.click(timeout=2000)
                self.page.wait_for_timeout(500)
                logger.info("Cookie banner dismissed via: %s", selector)
                return
            except Exception:
                continue

        logger.debug("No cookie banner dismissed")

    def click(self, selector: str) -> None:
        """Click the first element matching *selector*."""

        def _click() -> None:
            self.page.locator(selector).first.click()

        self._retry(f"click({selector})", _click)
        logger.info("Clicked selector: %s", selector)

    def fill(self, selector: str, value: str) -> None:
        """Fill an input or select-like element with *value*."""

        def _fill() -> None:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible")
            tag = locator.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                locator.select_option(label=value)
            else:
                locator.fill(value)

        self._retry(f"fill({selector})", _fill)
        logger.info("Filled selector %s with value: %s", selector, value)

    def hover(self, selector: str) -> None:
        """Hover over the element matching *selector*."""

        def _hover() -> None:
            self.page.locator(selector).first.hover()

        self._retry(f"hover({selector})", _hover)
        logger.debug("Hovered selector: %s", selector)

    def scroll_to_bottom(self, pause_ms: int = 500, max_rounds: int = 20) -> None:
        """Scroll down until the page height stops growing."""

        def _scroll() -> None:
            previous_height = 0
            for _ in range(max_rounds):
                current_height = self.page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    break
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.page.wait_for_timeout(pause_ms)
                previous_height = current_height

        self._retry("scroll_to_bottom", _scroll)
        logger.info("Scrolled to bottom")

    def extract_links(self, selector: str) -> list[dict[str, str]]:
        """Extract href/text pairs from anchors matching or nested under *selector*."""

        def _extract() -> list[dict[str, str]]:
            locator = self.page.locator(selector)
            count = locator.count()
            if count == 0:
                raise BrowserControllerError(f"No elements found for selector: {selector}")

            links: list[dict[str, str]] = []
            seen_hrefs: set[str] = set()

            for index in range(count):
                element = locator.nth(index)
                tag = element.evaluate("el => el.tagName.toLowerCase()")

                if tag == "a":
                    anchor = element
                else:
                    anchor = element.locator("a").first
                    if anchor.count() == 0:
                        continue

                href = anchor.get_attribute("href") or ""
                text = anchor.inner_text().strip()
                if not href or href in seen_hrefs:
                    continue

                absolute = urljoin(self._current_url or self.page.url, href)
                seen_hrefs.add(href)
                links.append({"href": absolute, "text": text})

            if not links:
                raise BrowserControllerError(f"No links extracted for selector: {selector}")
            return links

        links = self._retry(f"extract_links({selector})", _extract)
        logger.info("Links found: %d (selector=%s)", len(links), selector)
        return links

    def extract_hover_links(
        self,
        job_card_selector: str,
        link_selector: str,
    ) -> list[dict[str, str]]:
        """
        Hover each job card and extract the link revealed on hover.

        Used for career sites that only expose URLs after mouse-over.
        """

        def _extract() -> list[dict[str, str]]:
            cards = self.page.locator(job_card_selector)
            count = cards.count()
            if count == 0:
                raise BrowserControllerError(
                    f"No job cards found for selector: {job_card_selector}"
                )

            links: list[dict[str, str]] = []
            seen_hrefs: set[str] = set()

            for index in range(count):
                card = cards.nth(index)
                card.hover()
                self.page.wait_for_timeout(300)

                anchor = card.locator(link_selector).first
                if anchor.count() == 0:
                    anchor = self.page.locator(link_selector).nth(index)

                if anchor.count() == 0:
                    continue

                href = anchor.get_attribute("href") or ""
                text = anchor.inner_text().strip() or card.inner_text().strip()
                if not href or href in seen_hrefs:
                    continue

                absolute = urljoin(self._current_url or self.page.url, href)
                seen_hrefs.add(href)
                links.append({"href": absolute, "text": text})

            if not links:
                raise BrowserControllerError(
                    f"No hover links extracted (cards={job_card_selector}, "
                    f"links={link_selector})"
                )
            return links

        links = self._retry(
            f"extract_hover_links({job_card_selector})",
            _extract,
        )
        logger.info(
            "Hover links found: %d (cards=%s)",
            len(links),
            job_card_selector,
        )
        return links

    def next_page(self, selector: str) -> bool:
        """
        Click a pagination next button.

        Returns True when navigation succeeded, False when the button is
        missing or disabled (end of pagination).
        """

        def _next() -> bool:
            button = self.page.locator(selector).first
            if button.count() == 0:
                return False
            if not button.is_enabled() or not button.is_visible():
                return False
            button.click()
            self.page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
            return True

        try:
            clicked = self._retry(f"next_page({selector})", _next)
        except BrowserControllerError:
            logger.info("Next page not available (selector=%s)", selector)
            return False

        if clicked:
            logger.info("Next page clicked: %s", selector)
        else:
            logger.info("Pagination ended (selector=%s)", selector)
        return clicked

    def take_screenshot(self, path: str) -> None:
        """Save a full-page screenshot for debugging."""

        def _shot() -> None:
            self.page.screenshot(path=path, full_page=True)

        self._retry(f"take_screenshot({path})", _shot)
        logger.info("Screenshot saved: %s", path)

    def get_page_text(self, max_chars: int = 12_000) -> str:
        """Return visible page text for LLM analysis."""
        text = self.page.inner_text("body")
        return text[:max_chars]

    def get_page_html(self, max_chars: int = 0) -> str:
        """Return page HTML. Pass max_chars=0 (default) for the full document."""
        html = self.page.content()
        if max_chars and max_chars > 0:
            return html[:max_chars]
        return html

    def selector_exists(self, selector: str) -> bool:
        """Check whether at least one element matches *selector*."""
        return self.page.locator(selector).count() > 0

    def wait_for_selector(self, selector: str, timeout_ms: int | None = None) -> None:
        """Block until *selector* appears on the page."""

        def _wait() -> None:
            self.page.locator(selector).first.wait_for(
                state="visible",
                timeout=timeout_ms or self.timeout_ms,
            )

        self._retry(f"wait_for_selector({selector})", _wait)
