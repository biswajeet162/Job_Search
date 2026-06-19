"""Local LLM integration via Ollama HTTP API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)


class OllamaServiceError(Exception):
    """Raised when Ollama inference fails."""


class OllamaService:
    """
    Advisory LLM layer — recommends actions but never drives the browser.

    Uses the local Ollama server at http://localhost:11434.
    """

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "deepseek-r1:14b"
    DEFAULT_TIMEOUT_SEC = 180

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def ask(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to the local model and return the text response."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_sec,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            logger.debug("Ollama response received (%d chars)", len(content))
            return content.strip()
        except requests.RequestException as exc:
            raise OllamaServiceError(f"Ollama request failed: {exc}") from exc

    def analyze_page(self, page_content: str, company_name: str = "") -> dict[str, Any]:
        """
        Analyze career page content and identify job-related structure.

        Returns a dict with keys: summary, job_indicators, missing_info, confidence.
        """
        system = (
            "You are a career-page analysis assistant. "
            "You analyze HTML/text and return ONLY valid JSON. "
            "Never suggest executing browser commands directly."
        )
        prompt = f"""Analyze this career page content for company "{company_name}".

Identify:
1. Whether job listings are visible
2. Likely CSS selectors for job cards and links (if inferable)
3. What information appears missing (location, titles, pagination)
4. Confidence score 0.0-1.0

Return JSON only:
{{
  "summary": "brief description",
  "job_indicators": ["list of text snippets that look like jobs"],
  "suggested_selectors": {{
    "job_card": "css selector or null",
    "job_link": "css selector or null",
    "pagination": "css selector or null"
  }},
  "missing_info": ["list of missing fields"],
  "confidence": 0.0
}}

Page content:
{page_content[:10000]}
"""
        raw = self.ask(prompt, system=system)
        return self._parse_json_response(raw, fallback={
            "summary": "Analysis unavailable",
            "job_indicators": [],
            "suggested_selectors": {},
            "missing_info": ["LLM parse failed"],
            "confidence": 0.0,
        })

    def determine_next_action(self, context: str) -> dict[str, Any]:
        """
        Recommend the next advisory action when configured selectors fail.

        The agent maps recommendations to safe, predefined Playwright operations.
        Returns: action, reason, selector, value (optional).
        """
        system = (
            "You are an advisory agent for career page scraping. "
            "Recommend ONE next step from this list ONLY: "
            "scroll, wait, retry_extraction, analyze_again, abort, suggest_selector. "
            "Return ONLY valid JSON. Do NOT invent browser automation code."
        )
        prompt = f"""Given this context, what should the deterministic scraper try next?

Context:
{context[:8000]}

Return JSON only:
{{
  "action": "scroll|wait|retry_extraction|analyze_again|abort|suggest_selector",
  "reason": "why this action",
  "selector": "css selector if applicable else null",
  "value": "optional value"
}}
"""
        raw = self.ask(prompt, system=system)
        return self._parse_json_response(raw, fallback={
            "action": "retry_extraction",
            "reason": "LLM response could not be parsed",
            "selector": None,
            "value": None,
        })

    def health_check(self) -> bool:
        """Return True when Ollama is reachable."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _parse_json_response(
        self,
        raw: str,
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract JSON from model output (handles markdown fences and thinking tags)."""
        cleaned = raw.strip()

        # Strip reasoning-model thinking blocks (e.g. deepseek-r1 ...)
        for tag in ("think", "redacted_reasoning"):
            pattern = rf"<{tag}>.*?</{tag}>"
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()

        # Extract fenced JSON block if present
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1)

        # Find first JSON object
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON response; using fallback")
            return fallback
