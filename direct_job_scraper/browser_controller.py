"""Playwright browser abstraction for direct job link extraction."""

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
    """Playwright wrapper with retry handling for career page automation."""

    DEFAULT_TIMEOUT_MS = 30_000
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
        self._current_url: str = ""

    @property
    def page(self) -> Page:
        if self._page is None:
            raise BrowserControllerError("Browser not started. Call start() first.")
        return self._page

    def start(self) -> None:
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

    def _wait_for_settle(self, pause_ms: int = 2000) -> None:
        """Wait for page to settle; tolerate sites that never reach networkidle."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        if pause_ms > 0:
            self.page.wait_for_timeout(pause_ms)

    def open_url(self, url: str) -> None:
        def _navigate() -> None:
            self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self._wait_for_settle(pause_ms=2000)
            self._current_url = self.page.url

        self._retry(f"open_url({url})", _navigate)
        logger.info("Page opened: %s", self._current_url)

    def dismiss_page_overlays(self, custom_selectors: list[str] | None = None) -> None:
        """Dismiss cookie banners and site alert popups."""

        default_selectors = [
            "#onetrust-accept-btn-handler",
            "button#onetrust-accept-btn-handler",
            "button:has-text('Accept All Cookies')",
            "button:has-text('Accept All')",
            "button:has-text('Accept')",
            "button:has-text('I Accept')",
            "[data-testid='cookie-accept']",
            "#system-ialert .system-ialert-close-button",
            "#system-ialert button",
        ]
        selectors = custom_selectors if custom_selectors else default_selectors

        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if locator.count() == 0 or not locator.is_visible():
                    continue
                locator.click(timeout=2000)
                self.page.wait_for_timeout(500)
                logger.info("Overlay dismissed via: %s", selector)
            except Exception:
                continue

    def dismiss_cookie_banner(self) -> None:
        """Backward-compatible alias for overlay dismissal."""
        self.dismiss_page_overlays()

    def click(self, selector: str) -> None:
        def _click() -> None:
            self.page.locator(selector).first.click()

        self._retry(f"click({selector})", _click)
        logger.info("Clicked selector: %s", selector)

    def fill(self, selector: str, value: str) -> None:
        def _fill() -> None:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible")
            tag = locator.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                locator.select_option(label=value)
            else:
                locator.fill(value)

        self._retry(f"fill({selector})", _fill)
        logger.info("Filled %s with value: %s", selector, value)

    def select_dropdown(
        self,
        selector: str,
        value: str,
        match_by: str = "label",
    ) -> None:
        """Select an option from a native <select> element."""

        def _select() -> None:
            locator = self.page.locator(selector).first
            locator.wait_for(state="visible")
            if match_by == "value":
                locator.select_option(value=value)
            else:
                locator.select_option(label=value)

        self._retry(f"select_dropdown({selector})", _select)
        logger.info("Selected dropdown %s = %s", selector, value)

    def apply_facet_filter(
        self,
        open_selector: str,
        input_selector: str,
        value: str,
        option_selector: str,
        wait_ms: int = 1000,
    ) -> None:
        """Open a facet panel, search, and pick a checkbox/label option."""

        def _apply() -> None:
            open_loc = self.page.locator(open_selector).first
            open_loc.wait_for(state="visible", timeout=self.timeout_ms)
            open_loc.click()
            self.page.wait_for_timeout(400)

            input_loc = self.page.locator(input_selector).first
            input_loc.wait_for(state="visible", timeout=self.timeout_ms)
            input_loc.click()
            input_loc.fill(value)
            self.page.wait_for_timeout(wait_ms)

            option = self.page.locator(option_selector).first
            option.wait_for(state="attached", timeout=5000)
            try:
                option.click(timeout=3000)
            except Exception:
                option.click(force=True)
            self._wait_for_settle(pause_ms=1500)

        self._retry(f"apply_facet_filter({open_selector})", _apply)
        logger.info("Facet filter applied: %s → %s", value, option_selector)

    def apply_autocomplete(
        self,
        input_selector: str,
        value: str,
        option_selector: str | None = None,
        option_text: str | None = None,
        open_selector: str | None = None,
        wait_ms: int = 800,
    ) -> None:
        """Type into an autocomplete field and pick a suggestion."""

        def _apply() -> None:
            if open_selector:
                open_loc = self.page.locator(open_selector).first
                if open_loc.count() > 0 and open_loc.is_visible():
                    open_loc.click()
                    self.page.wait_for_timeout(300)

            input_loc = self.page.locator(input_selector).first
            input_loc.wait_for(state="visible")
            input_loc.click()
            input_loc.fill(value)
            self.page.wait_for_timeout(wait_ms)

            pick_text = option_text or value
            if option_selector:
                option = self.page.locator(option_selector).first
                option.wait_for(state="visible", timeout=self.timeout_ms)
                option.click()
            else:
                self.page.get_by_role("option", name=pick_text).first.click()

            self._wait_for_settle(pause_ms=1500)

        self._retry(f"apply_autocomplete({input_selector})", _apply)
        logger.info("Autocomplete filter applied: %s → %s", input_selector, value)

    def click_option(
        self,
        open_selector: str,
        option_selector: str,
        wait_ms: int = 500,
    ) -> None:
        """Open a custom dropdown and click an option."""

        def _click_option() -> None:
            self.page.locator(open_selector).first.click()
            self.page.wait_for_timeout(wait_ms)
            option = self.page.locator(option_selector).first
            option.wait_for(state="attached", timeout=5000)
            try:
                option.click(timeout=3000)
            except Exception:
                option.click(force=True)
            self._wait_for_settle(pause_ms=1500)

        self._retry(f"click_option({open_selector})", _click_option)
        logger.info("Clicked option via %s → %s", open_selector, option_selector)

    def wait_ms(self, ms: int) -> None:
        self.page.wait_for_timeout(ms)

    def hover(self, selector: str) -> None:
        def _hover() -> None:
            self.page.locator(selector).first.hover()

        self._retry(f"hover({selector})", _hover)

    def scroll_to_bottom(self, pause_ms: int = 500, max_rounds: int = 20) -> None:
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
                    f"No hover links extracted (cards={job_card_selector})"
                )
            return links

        links = self._retry(f"extract_hover_links({job_card_selector})", _extract)
        logger.info("Hover links found: %d", len(links))
        return links

    def toggle_facet_checkbox(
        self,
        checkbox_selector: str,
        open_selector: str | None = None,
        ensure_checked: bool = True,
    ) -> None:
        """Open facet panel (optional) and toggle a filter checkbox."""

        def _toggle() -> None:
            if open_selector:
                open_loc = self.page.locator(open_selector).first
                open_loc.wait_for(state="visible", timeout=self.timeout_ms)
                open_loc.click()
                self.page.wait_for_timeout(400)

            checkbox = self.page.locator(checkbox_selector).first
            checkbox.wait_for(state="attached", timeout=self.timeout_ms)
            is_checked = checkbox.is_checked()
            if ensure_checked and is_checked:
                return
            if not ensure_checked and not is_checked:
                return

            try:
                checkbox.click(timeout=3000)
            except Exception:
                label_for = checkbox.get_attribute("id")
                if label_for:
                    self.page.locator(f"label[for='{label_for}']").first.click(force=True)
                else:
                    checkbox.click(force=True)

            self._wait_for_settle(pause_ms=2000)

        self._retry(f"toggle_facet_checkbox({checkbox_selector})", _toggle)
        logger.info("Checkbox filter toggled: %s (checked=%s)", checkbox_selector, ensure_checked)

    def jump_to_page(
        self,
        page_number: int,
        input_selector: str,
        button_selector: str,
    ) -> bool:
        """Fill page number input and click 'Go to page'."""

        def _jump() -> bool:
            page_input = self.page.locator(input_selector).first
            if page_input.count() == 0:
                return False
            page_input.wait_for(state="visible", timeout=self.timeout_ms)
            page_input.fill(str(page_number))
            go_btn = self.page.locator(button_selector).first
            if go_btn.count() == 0:
                return False
            go_btn.click()
            self._wait_for_settle(pause_ms=2500)
            return True

        try:
            jumped = self._retry(f"jump_to_page({page_number})", _jump)
        except BrowserControllerError:
            logger.info("Page jump failed for page %d", page_number)
            return False

        if jumped:
            logger.info("Jumped to page %d via %s", page_number, button_selector)
        return jumped

    def extract_structured_cards(
        self,
        card_selector: str,
        link_selector: str,
        fields: dict[str, str] | None = None,
        attributes: dict[str, str] | None = None,
        attribute_scope: str = "link",
    ) -> list[dict[str, Any]]:
        """Extract jobs from cards using company-specific field and attribute selectors."""

        field_map = fields or {}
        attribute_map = attributes or {}

        def _extract() -> list[dict[str, Any]]:
            cards = self.page.locator(card_selector)
            count = cards.count()
            if count == 0:
                raise BrowserControllerError(f"No job cards found: {card_selector}")

            results: list[dict[str, Any]] = []
            seen: set[str] = set()

            for index in range(count):
                card = cards.nth(index)
                anchor = card.locator(link_selector).first
                if anchor.count() == 0:
                    continue

                href = anchor.get_attribute("href") or ""
                text = anchor.inner_text().strip()
                if not href:
                    continue

                absolute = urljoin(self._current_url or self.page.url, href)

                extracted_fields: dict[str, str] = {}
                for field_name, field_selector in field_map.items():
                    field_loc = card.locator(field_selector).first
                    if field_loc.count():
                        extracted_fields[field_name] = field_loc.inner_text().strip()

                extracted_attributes: dict[str, str] = {}
                scope = anchor if attribute_scope == "link" else card
                for logical_name, html_attribute in attribute_map.items():
                    value = scope.get_attribute(html_attribute) or ""
                    if value:
                        extracted_attributes[logical_name] = value.strip()

                dedupe_key = extracted_attributes.get("jobId") or absolute
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                results.append({
                    "href": absolute,
                    "text": text,
                    "fields": extracted_fields,
                    "attributes": extracted_attributes,
                })

            if not results:
                raise BrowserControllerError(f"No jobs extracted from cards: {card_selector}")
            return results

        results = self._retry(f"extract_structured_cards({card_selector})", _extract)
        logger.info("Structured cards found: %d (%s)", len(results), card_selector)
        return results

    def extract_job_cards(
        self,
        link_selector: str,
        card_selector: str,
        location_selector: str | None = None,
        job_id_attribute: str | None = None,
    ) -> list[dict[str, str]]:
        """Backward-compatible wrapper around extract_structured_cards."""

        fields = {"location": location_selector} if location_selector else {}
        attributes = {"jobId": job_id_attribute} if job_id_attribute else {}
        structured = self.extract_structured_cards(
            card_selector=card_selector,
            link_selector=link_selector,
            fields=fields,
            attributes=attributes,
            attribute_scope="link",
        )

        legacy: list[dict[str, str]] = []
        for item in structured:
            legacy.append({
                "href": item["href"],
                "text": item["text"],
                "jobId": item.get("attributes", {}).get("jobId", ""),
                "location": item.get("fields", {}).get("location", ""),
            })
        return legacy

    def next_page(self, selector: str) -> bool:
        def _next() -> bool:
            button = self.page.locator(selector).first
            if button.count() == 0:
                return False
            if not button.is_enabled() or not button.is_visible():
                return False
            button.click()
            self._wait_for_settle(pause_ms=2000)
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
        def _shot() -> None:
            self.page.screenshot(path=path, full_page=True)

        self._retry(f"take_screenshot({path})", _shot)
        logger.info("Screenshot saved: %s", path)

    def selector_exists(self, selector: str) -> bool:
        return self.page.locator(selector).count() > 0

    def wait_for_selector(self, selector: str, timeout_ms: int | None = None) -> None:
        def _wait() -> None:
            self.page.locator(selector).first.wait_for(
                state="visible",
                timeout=timeout_ms or self.timeout_ms,
            )

        self._retry(f"wait_for_selector({selector})", _wait)
