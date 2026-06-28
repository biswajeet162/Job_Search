"""CLI — extract job metrics from detail JSON (standalone or via pipeline worker)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from job_metrics_extractor import extract_job_metrics
from metrics_storage import MetricsStorage

BASE_DIR = Path(__file__).resolve().parent
DETAILS_DIR = BASE_DIR.parent / "2_get_job_details_using_job_link" / "job_details"
METRICS_DIR = BASE_DIR / "job_metrics"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create job metrics from detail JSON using local LLM")
    parser.add_argument("--detail-file", type=Path, help="Single detail JSON file")
    parser.add_argument("--all", action="store_true", help="Process all files in job_details/")
    parser.add_argument("--no-llm", action="store_true", help="Use regex fallback only")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    storage = MetricsStorage(METRICS_DIR)
    files: list[Path] = []

    if args.detail_file:
        files = [args.detail_file]
    elif args.all:
        files = sorted(DETAILS_DIR.glob("*.json"))
    else:
        print("Provide --detail-file or --all")
        return 1

    for path in files:
        with path.open(encoding="utf-8") as handle:
            detail = json.load(handle)
        source = detail.get("sourceJob", {})
        metrics = extract_job_metrics(
            detail,
            ollama_base_url=args.ollama_url,
            ollama_model=args.model,
            use_llm=not args.no_llm,
        )
        saved = storage.save_metrics(
            job_id=source.get("jobId", path.stem),
            company=source.get("company", "unknown"),
            source_detail_file=path.name,
            payload=metrics,
        )
        print(f"Saved: {saved.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
