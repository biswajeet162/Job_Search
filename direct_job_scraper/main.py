"""CLI for direct selector-based job scraping."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from agent import JobScraper
from errors import ScraperError
from browser_controller import BrowserController
from logger_util import setup_colored_logging

BASE_DIR = Path(__file__).resolve().parent
COMPANIES_DIR = BASE_DIR / "companies"
OUTPUT_DIR = BASE_DIR / "output"


def list_company_configs() -> list[Path]:
    return sorted(
        p for p in COMPANIES_DIR.glob("*.json")
        if not p.name.startswith("_")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Direct job scraper — extract job titles/URLs via CSS selectors "
            "and pagination (headless by default)"
        ),
    )
    parser.add_argument("--company", help="Company config (e.g. mastercard.json)")
    parser.add_argument("--all", action="store_true", help="Scrape all enabled companies")
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window (default: headless, no window)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args()


def resolve_config_path(company_arg: str) -> Path:
    candidate = Path(company_arg)
    if candidate.exists():
        return candidate.resolve()

    name = company_arg if company_arg.endswith(".json") else f"{company_arg}.json"
    config_path = COMPANIES_DIR / name
    if not config_path.exists():
        raise ScraperError(f"Company config not found: {config_path}")
    return config_path


def run_single(config_path: Path, headless: bool) -> int:
    browser = BrowserController(headless=headless)
    scraper = JobScraper(
        config_path=config_path,
        output_dir=OUTPUT_DIR,
        browser=browser,
    )

    try:
        result = scraper.run()
        logging.info(
            "Success: %d jobs from %s → %s",
            result["totalJobs"],
            config_path.name,
            result["_outputPaths"]["latest"],
        )
        return 0
    except ScraperError as exc:
        logging.error("Scrape failed for %s: %s", config_path.name, exc)
        return 1


def main() -> int:
    args = parse_args()
    setup_colored_logging(verbose=args.verbose)

    if not args.company and not args.all:
        available = [p.name for p in list_company_configs()]
        logging.error(
            "Specify --company <name.json> or --all. Available: %s",
            ", ".join(available) or "(none)",
        )
        return 1

    configs = list_company_configs() if args.all else [resolve_config_path(args.company)]
    if not configs:
        logging.error("No company configs in %s", COMPANIES_DIR)
        return 1

    headless = not args.visible
    exit_code = 0
    for config_path in configs:
        logging.info("Starting scrape: %s (headless=%s)", config_path.name, headless)
        if run_single(config_path, headless=headless) != 0:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
