"""Job queue operations — enqueue, claim, complete, fail."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pipeline.core.config import PipelineConfig
from pipeline.core.database import PipelineDatabase
from pipeline.core.models import Stage, Status, job_key, next_stage

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class PipelineQueue:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig.load()
        self.db = PipelineDatabase(self.config.db_path)

    def enqueue_discovered_jobs(self, jobs: list[dict[str, Any]]) -> int:
        """Called by project 1 when new jobs are found."""
        added = 0
        now = _now_iso()
        with self.db.transaction() as conn:
            for job in jobs:
                company = str(job.get("company", "")).strip()
                jid = str(job.get("jobId", "")).strip()
                url = str(job.get("jobUrl", "")).strip()
                if not company or not jid or not url:
                    continue
                key = job_key(company, jid)
                try:
                    conn.execute(
                        """
                        INSERT INTO pipeline_jobs (
                            job_key, company, job_id, job_title, job_url, location,
                            current_stage, stage_status, discovered_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            key,
                            company,
                            jid,
                            job.get("jobTitle", ""),
                            url,
                            job.get("location", ""),
                            Stage.DETAILS.value,
                            Status.PENDING.value,
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO pipeline_events (job_key, stage, status, message, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (key, Stage.DISCOVERED.value, Status.DONE.value, "New job enqueued", now),
                    )
                    added += 1
                except Exception:
                    # UNIQUE constraint — already in queue
                    continue
        if added:
            logger.info("Pipeline enqueued %d new job(s)", added)
        return added

    def claim_next(self, stage: Stage, worker_id: str = "worker") -> dict[str, Any] | None:
        """Atomically claim one pending job for a stage."""
        now = _now_iso()
        with self.db.transaction() as conn:
            row = conn.execute(
                """
                SELECT * FROM pipeline_jobs
                WHERE current_stage = ? AND stage_status = ?
                  AND retry_count < ?
                ORDER BY updated_at ASC
                LIMIT 1
                """,
                (stage.value, Status.PENDING.value, self.config.max_retries),
            ).fetchone()
            if not row:
                return None
            job = dict(row)
            conn.execute(
                """
                UPDATE pipeline_jobs
                SET stage_status = ?, updated_at = ?, error_message = NULL
                WHERE id = ? AND stage_status = ?
                """,
                (Status.PROCESSING.value, now, job["id"], Status.PENDING.value),
            )
            conn.execute(
                """
                INSERT INTO pipeline_events (job_key, stage, status, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job["job_key"],
                    stage.value,
                    Status.PROCESSING.value,
                    f"Claimed by {worker_id}",
                    now,
                ),
            )
            return job

    def complete_stage(
        self,
        job: dict[str, Any],
        *,
        artifact_file: str | None = None,
        message: str = "Stage completed",
    ) -> None:
        """Mark current stage done and advance to next stage pending."""
        now = _now_iso()
        stage = Stage(job["current_stage"])
        nxt = next_stage(stage)
        if nxt is None or nxt == Stage.COMPLETED:
            new_stage = Stage.COMPLETED.value
            new_status = Status.DONE.value
        else:
            new_stage = nxt.value
            new_status = Status.PENDING.value

        detail_file = job.get("detail_file")
        metrics_file = job.get("metrics_file")
        match_file = job.get("match_file")

        if stage == Stage.DETAILS and artifact_file:
            detail_file = artifact_file
        elif stage == Stage.METRICS and artifact_file:
            metrics_file = artifact_file
        elif stage == Stage.MATCH and artifact_file:
            match_file = artifact_file

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE pipeline_jobs
                SET current_stage = ?, stage_status = ?,
                    detail_file = ?, metrics_file = ?, match_file = ?,
                    retry_count = 0, error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    new_stage,
                    new_status,
                    detail_file,
                    metrics_file,
                    match_file,
                    now,
                    job["id"],
                ),
            )
            conn.execute(
                """
                INSERT INTO pipeline_events (job_key, stage, status, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job["job_key"], stage.value, Status.DONE.value, message, now),
            )

    def fail_stage(self, job: dict[str, Any], error: str) -> None:
        now = _now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE pipeline_jobs
                SET stage_status = ?, error_message = ?,
                    retry_count = retry_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (Status.FAILED.value, error[:2000], now, job["id"]),
            )
            conn.execute(
                """
                INSERT INTO pipeline_events (job_key, stage, status, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job["job_key"],
                    job["current_stage"],
                    Status.FAILED.value,
                    error[:500],
                    now,
                ),
            )

    def reset_failed_for_retry(self, stage: Stage | None = None) -> int:
        """Reset failed jobs back to pending (admin recovery)."""
        now = _now_iso()
        with self.db.transaction() as conn:
            if stage:
                cur = conn.execute(
                    """
                    UPDATE pipeline_jobs
                    SET stage_status = ?, error_message = NULL, updated_at = ?
                    WHERE stage_status = ? AND current_stage = ?
                      AND retry_count < ?
                    """,
                    (Status.PENDING.value, now, Status.FAILED.value, stage.value, self.config.max_retries),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE pipeline_jobs
                    SET stage_status = ?, error_message = NULL, updated_at = ?
                    WHERE stage_status = ? AND retry_count < ?
                    """,
                    (Status.PENDING.value, now, Status.FAILED.value, self.config.max_retries),
                )
            return cur.rowcount

    def get_stats(self) -> dict[str, Any]:
        by_stage = self.db.stats_by_stage()
        total = sum(row["count"] for row in by_stage)
        return {
            "totalJobs": total,
            "byStage": by_stage,
            "recentEvents": self.db.recent_events(20),
        }

    def backfill_from_job_list(self) -> int:
        """Import jobs from final_job_list.json not yet in queue."""
        import json

        path = self.config.job_list_path
        if not path or not path.exists():
            return 0
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        jobs = data.get("jobs", [])
        return self.enqueue_discovered_jobs(jobs)

    def reset_all(self) -> None:
        """Clear entire pipeline queue and event log."""
        self.db.clear_all_jobs()
        logger.info("Pipeline queue reset (all jobs cleared)")

    def enqueue_demo_jobs(
        self,
        company_limits: dict[str, int],
        job_list_path: Path | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Pick N jobs per company from final_job_list.json and enqueue.
        Example: {"Cognizant": 3, "HCLTech": 2}
        """
        import json

        path = job_list_path or self.config.job_list_path
        if not path or not path.exists():
            raise FileNotFoundError(f"Job list not found: {path}")

        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        all_jobs = data.get("jobs", [])
        picked: list[dict[str, Any]] = []
        counts = {k: 0 for k in company_limits}

        for job in all_jobs:
            company = str(job.get("company", ""))
            if company not in company_limits:
                continue
            if counts[company] >= company_limits[company]:
                continue
            if not job.get("jobId") or not job.get("jobUrl"):
                continue
            picked.append(job)
            counts[company] += 1
            if all(counts[c] >= company_limits[c] for c in company_limits):
                break

        added = self.enqueue_discovered_jobs(picked)

        demo_manifest = {
            "description": "Demo run: limited jobs for pipeline test (projects 1→2→3)",
            "companyLimits": company_limits,
            "picked": picked,
            "enqueued": added,
        }
        manifest_path = self.config.data_dir / "demo_job_list.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(demo_manifest, handle, indent=2, ensure_ascii=False)

        logger.info("Demo enqueued %d job(s): %s", added, counts)
        return picked, added

    def get_job_detail(self, job_key: str) -> dict[str, Any] | None:
        """Full job row + events + detail/metrics JSON file contents."""
        import json

        job = self.db.get_job_by_key(job_key)
        if not job:
            return None

        events = self.db.events_for_job(job_key)
        result: dict[str, Any] = {"job": job, "events": events}

        detail_file = job.get("detail_file")
        if detail_file:
            detail_path = self.config.details_dir / detail_file
            if detail_path.exists():
                with detail_path.open(encoding="utf-8") as handle:
                    result["detailJson"] = json.load(handle)

        metrics_file = job.get("metrics_file")
        if metrics_file:
            metrics_path = self.config.job_metrics_dir / metrics_file
            if metrics_path.exists():
                with metrics_path.open(encoding="utf-8") as handle:
                    result["metricsJson"] = json.load(handle)

        return result
