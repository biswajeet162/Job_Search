"""Staggered periodic scheduler — run each enabled company on a fixed cadence."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from heapq import heappop, heappush
from pathlib import Path

from errors import ScraperError
from logger_util import setup_colored_logging
from main import BASE_DIR, list_enabled_company_configs, run_single

SCHEDULER_CONFIG_PATH = BASE_DIR / "scheduler_config.json"
DEFAULT_STAGGER_SECONDS = 30
DEFAULT_INTERVAL_MINUTES = 15

_shutdown = threading.Event()


@dataclass(order=True)
class ScheduledRun:
    run_at: float
    company_index: int = field(compare=False)
    config_path: Path = field(compare=False)


def load_scheduler_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}

    with config_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_scheduler_settings(args: argparse.Namespace) -> tuple[int, int]:
    file_config = load_scheduler_config(SCHEDULER_CONFIG_PATH)

    stagger = (
        args.stagger_seconds
        if args.stagger_seconds is not None
        else file_config.get("staggerSeconds", DEFAULT_STAGGER_SECONDS)
    )
    interval = (
        args.interval_minutes
        if args.interval_minutes is not None
        else file_config.get("companyIntervalMinutes", DEFAULT_INTERVAL_MINUTES)
    )

    if stagger < 0:
        raise ScraperError("staggerSeconds must be >= 0")
    if interval <= 0:
        raise ScraperError("companyIntervalMinutes must be > 0")

    return stagger, interval


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run enabled company scrapers on a staggered schedule. "
            "Each company is triggered every N minutes; starts are offset "
            "by M seconds between companies. Runs do not wait for prior "
            "scrapes to finish."
        ),
    )
    parser.add_argument(
        "--stagger-seconds",
        type=int,
        default=None,
        help=(
            f"Seconds between each company's first trigger "
            f"(default: {DEFAULT_STAGGER_SECONDS} from scheduler_config.json)"
        ),
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=None,
        help=(
            f"Minutes between repeat triggers for the same company "
            f"(default: {DEFAULT_INTERVAL_MINUTES} from scheduler_config.json)"
        ),
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window (default: headless)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args()


def _format_run_time(monotonic_anchor: float, run_at: float) -> str:
    wall = datetime.fromtimestamp(time.time() + (run_at - monotonic_anchor))
    return wall.strftime("%H:%M:%S")


def _run_scrape(config_path: Path, headless: bool) -> None:
    company = config_path.stem
    started = datetime.now().strftime("%H:%M:%S")
    logging.info("[%s] Scrape started at %s", company, started)
    try:
        exit_code = run_single(config_path, headless=headless)
        status = "finished OK" if exit_code == 0 else f"finished with errors (code {exit_code})"
    except Exception:
        logging.exception("[%s] Scrape raised an unexpected error", company)
        status = "failed with exception"
    finished = datetime.now().strftime("%H:%M:%S")
    logging.info("[%s] Scrape %s at %s", company, status, finished)


def run_scheduler(
    *,
    stagger_seconds: int,
    interval_minutes: int,
    headless: bool,
) -> None:
    companies = list_enabled_company_configs()
    if not companies:
        raise ScraperError(f"No enabled company configs in {BASE_DIR / 'companies'}")

    interval_seconds = interval_minutes * 60
    anchor = time.monotonic()

    heap: list[ScheduledRun] = []
    for index, config_path in enumerate(companies):
        first_run = anchor + index * stagger_seconds
        heappush(heap, ScheduledRun(first_run, index, config_path))

    logging.info(
        "Scheduler started: %d companies, stagger=%ds, interval=%dm",
        len(companies),
        stagger_seconds,
        interval_minutes,
    )
    for index, config_path in enumerate(companies):
        first_at = anchor + index * stagger_seconds
        logging.info(
            "  [%d] %s → first at %s, then every %dm",
            index + 1,
            config_path.stem,
            _format_run_time(anchor, first_at),
            interval_minutes,
        )

    with ThreadPoolExecutor(max_workers=len(companies)) as executor:
        while not _shutdown.is_set():
            scheduled = heappop(heap)
            now = time.monotonic()
            wait_seconds = scheduled.run_at - now
            if wait_seconds > 0 and _shutdown.wait(timeout=wait_seconds):
                break

            if _shutdown.is_set():
                break

            company = scheduled.config_path.stem
            logging.info(
                "[%s] Triggering scrape (scheduled %s)",
                company,
                _format_run_time(anchor, scheduled.run_at),
            )
            executor.submit(_run_scrape, scheduled.config_path, headless)

            next_run = scheduled.run_at + interval_seconds
            heappush(
                heap,
                ScheduledRun(next_run, scheduled.company_index, scheduled.config_path),
            )

    logging.info("Scheduler stopped.")


def _handle_shutdown(signum: int, _frame: object) -> None:
    logging.info("Shutdown requested (signal %s), stopping after current wait…", signum)
    _shutdown.set()


def main() -> int:
    args = parse_args()
    setup_colored_logging(verbose=args.verbose)

    signal.signal(signal.SIGINT, _handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_shutdown)

    try:
        stagger_seconds, interval_minutes = resolve_scheduler_settings(args)
        run_scheduler(
            stagger_seconds=stagger_seconds,
            interval_minutes=interval_minutes,
            headless=not args.visible,
        )
    except ScraperError as exc:
        logging.error("%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
