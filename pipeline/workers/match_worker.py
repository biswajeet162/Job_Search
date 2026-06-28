"""Project 5 stub — match job metrics with resume metrics."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from pipeline.core.models import Stage
from pipeline.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class MatchWorker(BaseWorker):
    stage = Stage.MATCH
    name = "match-worker"

    def process(self, job: dict) -> str | None:
        metrics_file = job.get("metrics_file")
        if not metrics_file:
            raise FileNotFoundError(f"No metrics_file for {job['job_key']}")

        metrics_path = self.config.job_metrics_dir / metrics_file
        if not metrics_path.exists():
            raise FileNotFoundError(f"Metrics file missing: {metrics_path}")

        with metrics_path.open(encoding="utf-8") as handle:
            job_metrics = json.load(handle)

        resume_dir = self.config.resume_metrics_dir
        resume_files = list(resume_dir.glob("*.json")) if resume_dir.exists() else []

        matches = []
        job_skills = set(s.lower() for s in job_metrics.get("metrics", {}).get("skills", []))

        for resume_path in resume_files:
            with resume_path.open(encoding="utf-8") as handle:
                resume_data = json.load(handle)
            resume_skills = set(
                s.lower() for s in resume_data.get("metrics", {}).get("skills", [])
            )
            if not job_skills or not resume_skills:
                score = 0.0
                overlap: set[str] = set()
            else:
                overlap = job_skills & resume_skills
                score = round(len(overlap) / len(job_skills) * 100, 2)

            matches.append({
                "resumeKey": resume_data.get("resumeKey", resume_path.stem),
                "userId": resume_data.get("userId"),
                "matchScore": score,
                "matchedSkills": sorted(overlap) if job_skills and resume_skills else [],
            })

        matches.sort(key=lambda m: m["matchScore"], reverse=True)
        now = datetime.now().astimezone()
        ts = now.strftime("%Y%m%d-%H%M%S")
        filename = f"{job['job_id']}-{job['company'].lower().replace(' ', '-')}-{ts}-matches.json"
        out_path = self.config.matches_dir / filename

        payload = {
            "jobKey": job["job_key"],
            "jobId": job["job_id"],
            "company": job["company"],
            "sourceMetricsFile": metrics_file,
            "matchedAt": now.isoformat(timespec="seconds"),
            "matches": matches,
            "topMatchScore": matches[0]["matchScore"] if matches else 0,
        }
        with out_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        if not resume_files:
            logger.warning(
                "No resume metrics found — match scores are 0. Run project 4 when resumes are available."
            )

        return filename
