"""Run all pipeline workers concurrently with parallel threads per stage."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.core.config import PipelineConfig
from pipeline.core.queue import PipelineQueue
from pipeline.logger_util import setup_colored_logging
from pipeline.workers.details_worker import DetailsWorker
from pipeline.workers.match_worker import MatchWorker
from pipeline.workers.metrics_worker import MetricsWorker
from pipeline.workers.push_worker import PushWorker

logger = logging.getLogger(__name__)

WORKERS = {
    "details": DetailsWorker,
    "metrics": MetricsWorker,
    "match": MatchWorker,
    "push": PushWorker,
}

_shutdown = threading.Event()


def _handle_signal(signum, frame) -> None:
    logger.info("Shutdown signal received")
    _shutdown.set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pipeline workers 24/7 (parallel threads per stage)",
    )
    parser.add_argument(
        "--workers",
        nargs="+",
        choices=list(WORKERS.keys()) + ["all"],
        default=["all"],
        help="Which worker stages to run",
    )
    parser.add_argument("--visible", action="store_true", help="Show browser for details workers")
    parser.add_argument("--backfill", action="store_true", help="Enqueue all jobs from final_job_list.json")
    parser.add_argument("--backfill-only", action="store_true", help="Only backfill, do not start workers")
    parser.add_argument("--retry-failed", action="store_true", help="Reset failed jobs to pending")
    parser.add_argument(
        "--concurrency",
        type=int,
        help="Override parallel thread count for ALL selected workers",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def _worker_thread(
    worker_cls,
    config: PipelineConfig,
    headless: bool,
    instance_id: int,
) -> None:
    if worker_cls is DetailsWorker:
        worker = DetailsWorker(config, headless=headless, instance_id=instance_id)
    else:
        worker = worker_cls(config, instance_id=instance_id)

    logger.info("Thread started: %s", worker.name)
    while not _shutdown.is_set():
        try:
            if not worker.run_once():
                _shutdown.wait(config.worker_poll_seconds)
        except Exception as exc:
            logger.error("%s thread error: %s", worker.name, exc)
            _shutdown.wait(config.worker_poll_seconds)
    worker.stop()
    logger.info("Thread stopped: %s", worker.name)


def main() -> int:
    args = parse_args()
    setup_colored_logging(verbose=args.verbose)
    config = PipelineConfig.load()
    queue = PipelineQueue(config)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if args.backfill:
        count = queue.backfill_from_job_list()
        logger.info("Backfilled %d job(s) into pipeline queue", count)

    if args.retry_failed:
        count = queue.reset_failed_for_retry()
        logger.info("Reset %d failed job(s) to pending", count)

    if args.backfill_only:
        return 0

    selected = list(WORKERS.keys()) if "all" in args.workers else args.workers
    threads: list[threading.Thread] = []
    concurrency_summary: list[str] = []

    for name in selected:
        worker_cls = WORKERS[name]
        count = args.concurrency if args.concurrency else config.concurrency_for(name)
        concurrency_summary.append(f"{name}×{count}")

        for instance_id in range(1, count + 1):
            thread = threading.Thread(
                target=_worker_thread,
                args=(worker_cls, config, not args.visible, instance_id),
                name=f"pipeline-{name}-{instance_id}",
                daemon=True,
            )
            thread.start()
            threads.append(thread)

    total_threads = len(threads)
    logger.info(
        "Pipeline running — %d parallel threads: %s",
        total_threads,
        ", ".join(concurrency_summary),
    )
    logger.info("LLM model (job metrics): %s", config.model_for("job_metrics"))
    logger.info("Admin dashboard: python pipeline/admin/app.py")

    try:
        while not _shutdown.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown.set()

    for thread in threads:
        thread.join(timeout=15)

    return 0


if __name__ == "__main__":
    sys.exit(main())
