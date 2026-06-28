"""Staggered periodic scheduler — run each enabled company on a fixed cadence."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from heapq import heappop, heappush
from pathlib import Path

from errors import ScraperError
from logger_util import setup_colored_logging
from main import BASE_DIR, list_enabled_company_configs

SCHEDULER_CONFIG_PATH = BASE_DIR / "scheduler_config.json"
DEFAULT_STAGGER_SECONDS = 30
DEFAULT_INTERVAL_MINUTES = 15
DEFAULT_RUN_BATCH_FILE = "run_company.bat"
DEFAULT_SCHEDULE_PREVIEW_HOURS = 24
UPCOMING_PREVIEW_COUNT = 10

_shutdown = threading.Event()
_print_lock = threading.Lock()


@dataclass(frozen=True)
class SchedulerSettings:
    stagger_seconds: int
    interval_minutes: int
    run_batch_file: Path
    schedule_preview_hours: int


@dataclass(order=True)
class ScheduledRun:
    run_at: float
    company_index: int = field(compare=False)
    company_name: str = field(compare=False)


@dataclass(frozen=True)
class ScheduleEntry:
    at: datetime
    company: str
    is_next: bool = False


def load_scheduler_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}

    with config_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def resolve_scheduler_settings(args: argparse.Namespace) -> SchedulerSettings:
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
    batch_name = (
        args.run_batch_file
        if args.run_batch_file is not None
        else file_config.get("runBatchFile", DEFAULT_RUN_BATCH_FILE)
    )
    preview_hours = (
        args.schedule_preview_hours
        if args.schedule_preview_hours is not None
        else file_config.get("schedulePreviewHours", DEFAULT_SCHEDULE_PREVIEW_HOURS)
    )

    if stagger < 0:
        raise ScraperError("staggerSeconds must be >= 0")
    if interval <= 0:
        raise ScraperError("companyIntervalMinutes must be > 0")
    if preview_hours <= 0:
        raise ScraperError("schedulePreviewHours must be > 0")

    batch_path = Path(batch_name)
    if not batch_path.is_absolute():
        batch_path = BASE_DIR / batch_path
    if not batch_path.exists():
        raise ScraperError(f"Batch file not found: {batch_path}")

    return SchedulerSettings(
        stagger_seconds=stagger,
        interval_minutes=interval,
        run_batch_file=batch_path,
        schedule_preview_hours=preview_hours,
    )


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
        "--run-batch-file",
        default=None,
        help=(
            f"Batch file to launch per company; receives company name as %%1 "
            f"(default: {DEFAULT_RUN_BATCH_FILE} from scheduler_config.json)"
        ),
    )
    parser.add_argument(
        "--schedule-preview-hours",
        type=int,
        default=None,
        help=(
            f"Hours of schedule to print at startup "
            f"(default: {DEFAULT_SCHEDULE_PREVIEW_HOURS} from scheduler_config.json)"
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args()


def mono_to_wall(wall_anchor: datetime, mono_anchor: float, run_at: float) -> datetime:
    return wall_anchor + timedelta(seconds=run_at - mono_anchor)


def build_day_schedule(
    *,
    companies: list[str],
    wall_anchor: datetime,
    mono_anchor: float,
    stagger_seconds: int,
    interval_minutes: int,
    preview_hours: int,
    next_run_at: float | None = None,
) -> list[ScheduleEntry]:
    interval_seconds = interval_minutes * 60
    preview_end_mono = mono_anchor + preview_hours * 3600
    entries: list[ScheduleEntry] = []

    for index, company in enumerate(companies):
        run_at = mono_anchor + index * stagger_seconds
        while run_at < preview_end_mono:
            entries.append(
                ScheduleEntry(
                    at=mono_to_wall(wall_anchor, mono_anchor, run_at),
                    company=company,
                    is_next=next_run_at is not None and abs(run_at - next_run_at) < 0.001,
                )
            )
            run_at += interval_seconds

    entries.sort(key=lambda entry: entry.at)
    return entries


def _format_countdown(target: datetime) -> str:
    seconds = max(0, int((target - datetime.now()).total_seconds()))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def print_day_schedule(
    *,
    settings: SchedulerSettings,
    companies: list[str],
    wall_anchor: datetime,
    mono_anchor: float,
    next_run: ScheduledRun | None,
) -> None:
    next_mono = next_run.run_at if next_run else None
    entries = build_day_schedule(
        companies=companies,
        wall_anchor=wall_anchor,
        mono_anchor=mono_anchor,
        stagger_seconds=settings.stagger_seconds,
        interval_minutes=settings.interval_minutes,
        preview_hours=settings.schedule_preview_hours,
        next_run_at=next_mono,
    )

    divider = "=" * 72
    thin = "-" * 72

    with _print_lock:
        print()
        print(divider)
        print(
            f"  DAY SCHEDULE — next {settings.schedule_preview_hours}h "
            f"| stagger {settings.stagger_seconds}s "
            f"| interval {settings.interval_minutes}m "
            f"| batch {settings.run_batch_file.name}"
        )
        print(divider)

        if next_run:
            next_wall = mono_to_wall(wall_anchor, mono_anchor, next_run.run_at)
            print()
            print(
                f"  NEXT UP -> {next_wall.strftime('%H:%M:%S')}  "
                f"{next_run.company_name}  (in {_format_countdown(next_wall)})"
            )

        print()
        print(f"  {'Time':<10}  {'Company':<16}  Note")
        print(f"  {thin}")

        for entry in entries:
            marker = " <- NEXT" if entry.is_next else ""
            print(
                f"  {entry.at.strftime('%H:%M:%S'):<10}  "
                f"{entry.company:<16}  {marker}"
            )

        print()
        print("  Per company:")
        runs_by_company: dict[str, list[datetime]] = {}
        for entry in entries:
            runs_by_company.setdefault(entry.company, []).append(entry.at)

        for company in companies:
            times = runs_by_company.get(company, [])
            if not times:
                continue
            preview = ", ".join(t.strftime("%H:%M:%S") for t in times[:6])
            extra = ""
            if len(times) > 6:
                extra = f", ... (+{len(times) - 6} more)"
            print(f"    {company:<14} {len(times):>3} runs -> {preview}{extra}")

        print(divider)
        print()


def print_upcoming_runs(
    *,
    settings: SchedulerSettings,
    companies: list[str],
    wall_anchor: datetime,
    mono_anchor: float,
    heap: list[ScheduledRun],
) -> None:
    upcoming = sorted(heap)[:UPCOMING_PREVIEW_COUNT]
    thin = "-" * 72

    with _print_lock:
        print()
        print("  UPCOMING RUNS")
        print(f"  {thin}")
        for index, scheduled in enumerate(upcoming):
            wall_time = mono_to_wall(wall_anchor, mono_anchor, scheduled.run_at)
            label = "NEXT" if index == 0 else f"+{index}"
            print(
                f"  {label:<5} {wall_time.strftime('%H:%M:%S')}  "
                f"{scheduled.company_name}  (in {_format_countdown(wall_time)})"
            )
        print(f"  {thin}")
        print()


def launch_company_batch(batch_path: Path, company: str) -> None:
    started = datetime.now().strftime("%H:%M:%S")
    logging.info("[%s] Launching %s at %s", company, batch_path.name, started)

    try:
        process = subprocess.Popen(
            ["cmd", "/c", str(batch_path), company],
            cwd=str(BASE_DIR),
        )
        exit_code = process.wait()
        status = "finished OK" if exit_code == 0 else f"finished with errors (code {exit_code})"
    except Exception:
        logging.exception("[%s] Batch launch failed", company)
        status = "failed with exception"

    finished = datetime.now().strftime("%H:%M:%S")
    logging.info("[%s] Batch %s at %s", company, status, finished)


def run_scheduler(settings: SchedulerSettings) -> None:
    config_paths = list_enabled_company_configs()
    if not config_paths:
        raise ScraperError(f"No enabled company configs in {BASE_DIR / 'companies'}")

    companies = [path.stem for path in config_paths]
    interval_seconds = settings.interval_minutes * 60
    wall_anchor = datetime.now()
    mono_anchor = time.monotonic()

    heap: list[ScheduledRun] = []
    for index, company in enumerate(companies):
        first_run = mono_anchor + index * settings.stagger_seconds
        heappush(heap, ScheduledRun(first_run, index, company))

    logging.info(
        "Scheduler started: %d companies, stagger=%ds, interval=%dm, batch=%s",
        len(companies),
        settings.stagger_seconds,
        settings.interval_minutes,
        settings.run_batch_file.name,
    )

    print_day_schedule(
        settings=settings,
        companies=companies,
        wall_anchor=wall_anchor,
        mono_anchor=mono_anchor,
        next_run=heap[0] if heap else None,
    )
    print_upcoming_runs(
        settings=settings,
        companies=companies,
        wall_anchor=wall_anchor,
        mono_anchor=mono_anchor,
        heap=heap,
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

            wall_time = mono_to_wall(wall_anchor, mono_anchor, scheduled.run_at)
            logging.info(
                "[%s] Triggering batch (scheduled %s)",
                scheduled.company_name,
                wall_time.strftime("%H:%M:%S"),
            )
            executor.submit(launch_company_batch, settings.run_batch_file, scheduled.company_name)

            next_run = scheduled.run_at + interval_seconds
            heappush(
                heap,
                ScheduledRun(next_run, scheduled.company_index, scheduled.company_name),
            )

            print_upcoming_runs(
                settings=settings,
                companies=companies,
                wall_anchor=wall_anchor,
                mono_anchor=mono_anchor,
                heap=heap,
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
        settings = resolve_scheduler_settings(args)
        run_scheduler(settings)
    except ScraperError as exc:
        logging.error("%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
