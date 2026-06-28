"""Project 6 stub — push matched jobs to cloud backend."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from pipeline.core.models import Stage
from pipeline.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class PushWorker(BaseWorker):
    stage = Stage.PUSH
    name = "push-worker"

    def process(self, job: dict) -> str | None:
        match_file = job.get("match_file")
        if not match_file:
            raise FileNotFoundError(f"No match_file for {job['job_key']}")

        match_path = self.config.matches_dir / match_file
        if not match_path.exists():
            raise FileNotFoundError(f"Match file missing: {match_path}")

        with match_path.open(encoding="utf-8") as handle:
            match_data = json.load(handle)

        metrics_file = job.get("metrics_file")
        job_payload: dict = {}
        if metrics_file:
            metrics_path = self.config.job_metrics_dir / metrics_file
            if metrics_path.exists():
                with metrics_path.open(encoding="utf-8") as handle:
                    job_payload = json.load(handle)

        api_url = f"{self.config.cloud_api_base_url.rstrip('/')}/api/pipeline/jobs"
        body = json.dumps({
            "jobKey": job["job_key"],
            "job": job_payload,
            "matches": match_data.get("matches", []),
        }).encode("utf-8")

        request = urllib.request.Request(
            api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status >= 400:
                    raise RuntimeError(f"Cloud API returned {response.status}")
        except urllib.error.URLError as exc:
            # Backend not live yet — log and still complete so pipeline doesn't block
            logger.warning(
                "Cloud API not reachable (%s) — saving locally only. "
                "Start 0_job_search_backend to enable push.",
                exc,
            )

        return match_file
