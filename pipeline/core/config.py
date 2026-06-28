"""Paths and settings for the local pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PipelineConfig:
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)
    data_dir: Path = field(default_factory=lambda: REPO_ROOT / "pipeline_data")
    db_path: Path | None = None

    project1_dir: Path = field(default_factory=lambda: REPO_ROOT / "1_scrape_job_careers_pages")
    project2_dir: Path = field(default_factory=lambda: REPO_ROOT / "2_get_job_details_using_job_link")
    project3_dir: Path = field(default_factory=lambda: REPO_ROOT / "3_create_job_metrics_using_llm")
    project4_dir: Path = field(default_factory=lambda: REPO_ROOT / "4_create_resume_metrics_using_llm")
    project5_dir: Path = field(default_factory=lambda: REPO_ROOT / "5_match_resume_with_job_metrics")
    project6_dir: Path = field(default_factory=lambda: REPO_ROOT / "6_push_jobs_to_cloud_db")

    job_list_path: Path | None = None
    details_dir: Path | None = None
    job_metrics_dir: Path | None = None
    resume_metrics_dir: Path | None = None
    matches_dir: Path | None = None

    max_retries: int = 3
    worker_poll_seconds: float = 5.0
    worker_batch_size: int = 10

    # Parallel worker threads per pipeline stage
    worker_concurrency: dict[str, int] = field(default_factory=lambda: {
        "details": 3,
        "metrics": 2,
        "match": 2,
        "push": 1,
    })

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_models: dict[str, str] = field(default_factory=lambda: {
        "job_metrics": "llama3.1:8b",
        "resume_metrics": "llama3.1:8b",
        "embeddings": "nomic-embed-text:latest",
        "code": "qwen2.5-coder:1.5b-base",
        "reasoning": "deepseek-r1:14b",
    })
    cloud_api_base_url: str = "http://localhost:8000"

    def concurrency_for(self, worker_name: str) -> int:
        return max(1, int(self.worker_concurrency.get(worker_name, 1)))

    def model_for(self, task: str) -> str:
        return self.ollama_models.get(task, self.ollama_model)

    def __post_init__(self) -> None:
        if self.db_path is None:
            self.db_path = self.data_dir / "pipeline.db"
        if self.job_list_path is None:
            self.job_list_path = self.project1_dir / "jobs_dashboard" / "final_job_list.json"
        if self.details_dir is None:
            self.details_dir = self.project2_dir / "job_details"
        if self.job_metrics_dir is None:
            self.job_metrics_dir = self.project3_dir / "job_metrics"
        if self.resume_metrics_dir is None:
            self.resume_metrics_dir = self.project4_dir / "resume_metrics"
        if self.matches_dir is None:
            self.matches_dir = self.project5_dir / "matches"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.details_dir.mkdir(parents=True, exist_ok=True)
        self.job_metrics_dir.mkdir(parents=True, exist_ok=True)
        self.resume_metrics_dir.mkdir(parents=True, exist_ok=True)
        self.matches_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load(cls, config_path: Path | None = None) -> PipelineConfig:
        path = config_path or (REPO_ROOT / "pipeline" / "config.json")
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
        cfg = cls()
        for key, value in raw.items():
            if hasattr(cfg, key):
                if key.endswith("_dir") or key.endswith("_path") or key == "repo_root":
                    setattr(cfg, key, Path(value))
                elif key in ("worker_concurrency", "ollama_models") and isinstance(value, dict):
                    getattr(cfg, key).update(value)
                else:
                    setattr(cfg, key, value)
        cfg.__post_init__()
        return cfg
