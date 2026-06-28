"""Extract structured job metrics from detail JSON using local LLM."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from llm.ollama_client import chat_json

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "job_metrics_v1.txt"
PROMPT_VERSION = "1.0"


def _build_prompt(template: str, title: str, location: str, description: str) -> str:
    """Substitute job fields without breaking JSON braces in the prompt template."""
    return (
        template.replace("{title}", title)
        .replace("{location}", location)
        .replace("{description}", description[:12000])
    )


def _regex_years(text: str) -> dict[str, Any]:
    patterns = [
        r"minimum of (\d+)\s*years?",
        r"(?:minimum|min\.?|at least)\s+(\d+)\s*(?:\+)?\s*years?",
        r"(\d+)\s*[-–to]+\s*(\d+)\s*years?",
        r"(\d+)\s*\+\s*years?",
        r"(\d+)\s*years?\s+(?:of\s+)?experience",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        groups = [g for g in match.groups() if g]
        if len(groups) == 2:
            return {"min": int(groups[0]), "max": int(groups[1]), "raw": match.group(0)}
        if len(groups) == 1:
            val = int(groups[0])
            return {"min": val, "max": val, "raw": match.group(0)}
    return {"min": None, "max": None, "raw": ""}


def _fallback_extract(detail_data: dict[str, Any]) -> dict[str, Any]:
    details = detail_data.get("details", {})
    source = detail_data.get("sourceJob", {})
    description = details.get("description") or ""
    title = details.get("title") or source.get("jobTitle", "")
    location = details.get("location") or source.get("location", "")

    skills: list[str] = []
    tech_pattern = re.findall(
        r"\b(?:Python|Java|JavaScript|TypeScript|SQL|AWS|Azure|GCP|Kubernetes|Docker|"
        r"React|Angular|Node\.js|Spring|\.NET|C\+\+|Go|Rust|Scala|Kafka|Spark|"
        r"Databricks|Snowflake|Terraform|Ansible|Jenkins|Git|Linux|Maximo|SAP|Oracle)\b",
        description,
        re.IGNORECASE,
    )
    skills = sorted(set(s.strip() for s in tech_pattern if s), key=str.lower)

    return {
        "jobTitle": title,
        "description": description,
        "yearsOfExperience": _regex_years(description),
        "location": location,
        "skills": skills,
    }


def extract_job_metrics(
    detail_data: dict[str, Any],
    *,
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.1:8b",
    use_llm: bool = True,
) -> dict[str, Any]:
    details = detail_data.get("details", {})
    source = detail_data.get("sourceJob", {})
    title = details.get("title") or source.get("jobTitle", "")
    location = details.get("location") or source.get("location", "")
    description = details.get("description") or ""

    metrics: dict[str, Any]
    extraction_method = "llm"

    if use_llm and description:
        try:
            logger.info("METRICS LLM start — title=%s", title[:60])
            prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
            prompt = _build_prompt(prompt_template, title, location, description)
            llm_result = chat_json(
                prompt=prompt,
                base_url=ollama_base_url,
                model=ollama_model,
            )
            metrics = {
                "jobTitle": llm_result.get("jobTitle") or title,
                "description": llm_result.get("description") or description,
                "yearsOfExperience": llm_result.get("yearsOfExperience") or _regex_years(description),
                "location": llm_result.get("location") or location,
                "skills": llm_result.get("skills") or [],
            }
        except Exception as exc:
            logger.warning("METRICS LLM failed, using regex fallback: %s", exc)
            metrics = _fallback_extract(detail_data)
            extraction_method = "regex_fallback"
    else:
        metrics = _fallback_extract(detail_data)
        extraction_method = "regex_fallback"

    if not metrics.get("skills"):
        fallback = _fallback_extract(detail_data)
        metrics["skills"] = fallback.get("skills", [])

    now = datetime.now().astimezone()
    return {
        "jobId": source.get("jobId", ""),
        "company": source.get("company", ""),
        "sourceDetailFile": "",
        "extractedAt": now.isoformat(timespec="seconds"),
        "extractionMethod": extraction_method,
        "promptVersion": PROMPT_VERSION,
        "llm": {"provider": "ollama", "model": ollama_model},
        "metrics": metrics,
    }
