"""CLI entry point — fetch raw HTML from company page URLs defined in JSON configs."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from fetcher import FetcherError, PageFetcher
from browser_controller import BrowserController

BASE_DIR = Path(__file__).resolve().parent
COMPANIES_DIR = BASE_DIR / "companies"
DATA_DIR = BASE_DIR / "data"


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def list_company_configs() -> list[Path]:
    return sorted(
        p for p in COMPANIES_DIR.glob("*.json")
        if not p.name.startswith("_")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch raw HTML from hard-coded career page URLs. "
            "Company configs live in companies/*.json"
        ),
    )
    parser.add_argument(
        "--company",
        help="Company config filename (e.g. mastercard.json) or full path",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all enabled company configs in companies/",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (default: visible mode)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def resolve_config_path(company_arg: str) -> Path:
    candidate = Path(company_arg)
    if candidate.exists():
        return candidate.resolve()

    name = company_arg if company_arg.endswith(".json") else f"{company_arg}.json"
    config_path = COMPANIES_DIR / name
    if not config_path.exists():
        raise FetcherError(f"Company config not found: {config_path}")
    return config_path


def run_single(config_path: Path, headless: bool) -> int:
    browser = BrowserController(headless=headless)
    fetcher = PageFetcher(
        config_path=config_path,
        data_dir=DATA_DIR,
        browser=browser,
    )

    try:
        run_dir = fetcher.run()
        logging.info("Stored under: %s", run_dir)
        return 0
    except FetcherError as exc:
        logging.error("Fetch failed for %s: %s", config_path.name, exc)
        return 1


def main() -> int:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    if not args.company and not args.all:
        available = [p.name for p in list_company_configs()]
        logging.error(
            "Specify --company <name.json> or --all. Available: %s",
            ", ".join(available) or "(none — add JSON files under companies/)",
        )
        return 1

    configs: list[Path] = []
    if args.all:
        configs = list_company_configs()
        if not configs:
            logging.error("No company configs found in %s", COMPANIES_DIR)
            return 1
    else:
        configs = [resolve_config_path(args.company)]

    exit_code = 0
    for config_path in configs:
        logging.info("Starting fetch: %s", config_path.name)
        if run_single(config_path, headless=args.headless) != 0:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
