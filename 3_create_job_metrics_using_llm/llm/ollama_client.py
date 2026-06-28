"""Ollama client for local LLM extraction."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def check_ollama(base_url: str = "http://localhost:11434", timeout: int = 5) -> dict[str, Any]:
    """Ping Ollama and return online status + installed models."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        return {"online": True, "baseUrl": base_url, "models": models}
    except Exception as exc:
        return {"online": False, "baseUrl": base_url, "models": [], "error": str(exc)}


def chat_json(
    *,
    prompt: str,
    base_url: str = "http://localhost:11434",
    model: str = "llama3.1:8b",
    timeout: int = 120,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/chat"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    logger.info("OLLAMA calling model=%s (prompt ~%d chars, timeout=%ds)...", model, len(prompt), timeout)
    started = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        elapsed = time.perf_counter() - started
        logger.error("OLLAMA failed after %.1fs — not reachable: %s", elapsed, exc)
        raise RuntimeError(
            f"Ollama not reachable at {base_url}. Start Ollama and pull model: ollama pull {model}"
        ) from exc

    elapsed = time.perf_counter() - started
    content = payload.get("message", {}).get("content", "")
    if not content:
        logger.error("OLLAMA empty response after %.1fs", elapsed)
        raise RuntimeError("Empty LLM response")

    try:
        result = json.loads(content)
        logger.info(
            "OLLAMA done in %.1fs — model=%s, skills=%d, title=%s",
            elapsed,
            model,
            len(result.get("skills", [])),
            (result.get("jobTitle") or "")[:50],
        )
        return result
    except json.JSONDecodeError as exc:
        logger.error("OLLAMA invalid JSON after %.1fs: %s", elapsed, content[:200])
        raise RuntimeError(f"LLM returned invalid JSON: {content[:200]}") from exc
