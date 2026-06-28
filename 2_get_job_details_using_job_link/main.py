"""CLI — scrape full job details from final_job_list.json job URLs."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from logger_util import setup_colored_logging
from scraper import DEFAULT_JOB_LIST, JobDetailScraper

BASE_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape detailed job pages for each entry in final_job_list.json. "
            "Outputs job_details/{jobId}-{company}-{timestamp}.json"
        ),
    )
    parser.add_argument(
        "--job-list",
        type=Path,
        default=DEFAULT_JOB_LIST,
        help="Path to final_job_list.json from project 1",
    )
    parser.add_argument("--company", help="Only scrape jobs for this company")
    parser.add_argument("--limit", type=int, help="Max number of new jobs to scrape")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape jobs even if already in scraped_registry.json",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window (default: headless)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_colored_logging(verbose=args.verbose)

    try:
        scraper = JobDetailScraper(
            base_dir=BASE_DIR,
            job_list_path=args.job_list.resolve(),
            headless=not args.visible,
        )
        stats = scraper.run(
            company=args.company,
            limit=args.limit,
            force=args.force,
        )
    except Exception as exc:
        logging.getLogger(__name__).error("Scraper failed: %s", exc)
        if args.verbose:
            raise
        return 1

    return 0 if stats["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
