"""Base class for pipeline stage workers."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from pipeline.core.config import PipelineConfig
from pipeline.core.models import Stage
from pipeline.core.queue import PipelineQueue

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    stage: Stage
    name: str = "worker"

    def __init__(
        self,
        config: PipelineConfig | None = None,
        *,
        instance_id: int = 1,
    ) -> None:
        self.config = config or PipelineConfig.load()
        self.queue = PipelineQueue(self.config)
        self._running = False
        if instance_id > 1:
            self.name = f"{self.name}-{instance_id}"

    @abstractmethod
    def process(self, job: dict) -> str | None:
        """Process one job. Return artifact filename/path or None."""

    def run_once(self) -> bool:
        job = self.queue.claim_next(self.stage, worker_id=self.name)
        if not job:
            return False
        logger.info(
            "[%s] Processing %s | %s | stage=%s",
            self.name,
            job.get("job_id"),
            job.get("company"),
            self.stage.value,
        )
        try:
            artifact = self.process(job)
            self.queue.complete_stage(
                job,
                artifact_file=artifact,
                message=f"{self.stage.value} completed by {self.name}",
            )
            logger.info(
                "[%s] Done %s | %s",
                self.name,
                job.get("job_id"),
                job.get("company"),
            )
        except Exception as exc:
            logger.error(
                "[%s] Failed %s | %s: %s",
                self.name,
                job.get("job_id"),
                job.get("company"),
                exc,
            )
            self.queue.fail_stage(job, str(exc))
        return True

    def run_loop(self) -> None:
        self._running = True
        logger.info("[%s] Started (poll=%ss)", self.name, self.config.worker_poll_seconds)
        while self._running:
            processed = self.run_once()
            if not processed:
                time.sleep(self.config.worker_poll_seconds)

    def stop(self) -> None:
        self._running = False
