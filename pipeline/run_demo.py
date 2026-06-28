"""
Demo pipeline run — small proof for projects 1→2→3.

Clears the queue, picks 3 Cognizant + 2 HCLTech jobs, enqueues them,
and optionally processes through details + metrics (Ollama).

Usage:
  python pipeline/run_demo.py              # reset + enqueue 5 jobs
  python pipeline/run_demo.py --process    # also run workers until metrics done
"""

from __future__ import annotations

import argparse
import logging
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
from pipeline.workers.metrics_worker import MetricsWorker

DEMO_COMPANIES = {"Cognizant": 3, "HCLTech": 2}
METRICS_DONE_STAGES = {"match", "push", "completed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo: 3 Cognizant + 2 HCLTech through project 3")
    parser.add_argument("--process", action="store_true", help="Run details+metrics workers until all 5 finish")
    parser.add_argument("--no-reset", action="store_true", help="Do not clear existing queue before enqueue")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--timeout", type=int, default=900, help="Max seconds to wait in --process mode")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def _worker_loop(worker, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        if not worker.run_once():
            stop_event.wait(2)


def _demo_progress(queue: PipelineQueue, job_keys: list[str]) -> dict[str, int]:
    counts = {"pending": 0, "processing": 0, "metrics_done": 0, "failed": 0}
    for key in job_keys:
        job = queue.db.get_job_by_key(key)
        if not job:
            continue
        stage = job["current_stage"]
        status = job["stage_status"]
        if status == "failed":
            counts["failed"] += 1
        elif stage in METRICS_DONE_STAGES:
            counts["metrics_done"] += 1
        elif status == "processing":
            counts["processing"] += 1
        else:
            counts["pending"] += 1
    return counts


def main() -> int:
    args = parse_args()
    setup_colored_logging(verbose=args.verbose)
    logger = logging.getLogger("demo")

    config = PipelineConfig.load()
    queue = PipelineQueue(config)

    if not args.no_reset:
        queue.reset_all()
        logger.info("Pipeline queue cleared")

    picked, added = queue.enqueue_demo_jobs(DEMO_COMPANIES)

    from pipeline.core.models import job_key as make_key

    job_keys = [make_key(j["company"], str(j["jobId"])) for j in picked]

    print("\n=== DEMO JOB LIST (5 jobs) ===")
    for j in picked:
        print(f"  [{j['company']}] {j['jobId']} — {j.get('jobTitle', '')[:50]}")
    print(f"\nEnqueued: {added} jobs")
    print(f"Manifest: {config.data_dir / 'demo_job_list.json'}")

    if not args.process:
        print("\nNext steps:")
        print("  1. python pipeline/admin/app.py          -> http://localhost:8090")
        print("  2. python pipeline/run_workers.py --workers details metrics")
        print("  Or: python pipeline/run_demo.py --process")
        return 0

    stop = threading.Event()
    details = DetailsWorker(config, headless=not args.visible, instance_id=1)
    metrics = MetricsWorker(config, instance_id=1)
    threads = [
        threading.Thread(target=_worker_loop, args=(details, stop), name="demo-details", daemon=True),
        threading.Thread(target=_worker_loop, args=(metrics, stop), name="demo-metrics", daemon=True),
    ]
    for t in threads:
        t.start()

    logger.info("Processing demo jobs (details -> metrics via Ollama %s)...", config.model_for("job_metrics"))
    deadline = time.time() + args.timeout

    try:
        while time.time() < deadline:
            prog = _demo_progress(queue, job_keys)
            logger.info(
                "Progress: metrics_done=%d processing=%d pending=%d failed=%d",
                prog["metrics_done"],
                prog["processing"],
                prog["pending"],
                prog["failed"],
            )
            if prog["metrics_done"] == len(job_keys):
                logger.info("All %d demo jobs completed through project 3 (metrics)!", len(job_keys))
                break
            if prog["failed"] > 0 and prog["processing"] == 0 and prog["pending"] == 0:
                logger.error("Demo stopped: %d job(s) failed", prog["failed"])
                break
            time.sleep(3)
        else:
            logger.error("Demo timed out after %ds", args.timeout)
            return 1
    finally:
        stop.set()
        details.stop()
        for t in threads:
            t.join(timeout=10)

    print("\n=== RESULTS ===")
    for key in job_keys:
        detail = queue.get_job_detail(key)
        if not detail:
            continue
        job = detail["job"]
        metrics = detail.get("metricsJson", {}).get("metrics", {})
        skills = metrics.get("skills", [])
        print(f"\n{key}")
        print(f"  Stage: {job['current_stage']} / {job['stage_status']}")
        print(f"  Title: {metrics.get('jobTitle', job.get('job_title', ''))}")
        print(f"  Skills ({len(skills)}): {', '.join(skills[:12])}{'...' if len(skills) > 12 else ''}")
        if job.get("metrics_file"):
            print(f"  Metrics file: {config.job_metrics_dir / job['metrics_file']}")

    print("\nOpen http://localhost:8090 and click any job row for full detail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
