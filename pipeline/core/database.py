"""SQLite persistence for pipeline jobs, resumes, events."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS pipeline_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_key         TEXT NOT NULL UNIQUE,
    company         TEXT NOT NULL,
    job_id          TEXT NOT NULL,
    job_title       TEXT,
    job_url         TEXT NOT NULL,
    location        TEXT,
    current_stage   TEXT NOT NULL DEFAULT 'details',
    stage_status    TEXT NOT NULL DEFAULT 'pending',
    detail_file     TEXT,
    metrics_file    TEXT,
    match_file      TEXT,
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    discovered_at   TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_stage_status
    ON pipeline_jobs(current_stage, stage_status);

CREATE INDEX IF NOT EXISTS idx_jobs_updated
    ON pipeline_jobs(updated_at DESC);

CREATE TABLE IF NOT EXISTS pipeline_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_key     TEXT NOT NULL,
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL,
    message     TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_job_key
    ON pipeline_events(job_key, created_at DESC);

CREATE TABLE IF NOT EXISTS resume_pipeline (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    resume_key      TEXT NOT NULL UNIQUE,
    user_id         TEXT,
    resume_file     TEXT,
    metrics_file    TEXT,
    current_stage   TEXT NOT NULL DEFAULT 'resume_metrics',
    stage_status    TEXT NOT NULL DEFAULT 'pending',
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resume_stage_status
    ON resume_pipeline(current_stage, stage_status);

CREATE TABLE IF NOT EXISTS job_resume_matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_key         TEXT NOT NULL,
    resume_key      TEXT NOT NULL,
    match_score     REAL,
    match_file      TEXT,
    pushed_at       TEXT,
    created_at      TEXT NOT NULL,
    UNIQUE(job_key, resume_key)
);
"""


class PipelineDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple[Any, ...] | dict[str, Any] = ()) -> sqlite3.Cursor:
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]

    def stats_by_stage(self) -> list[dict[str, Any]]:
        return self.fetchall(
            """
            SELECT current_stage, stage_status, COUNT(*) AS count
            FROM pipeline_jobs
            GROUP BY current_stage, stage_status
            ORDER BY current_stage, stage_status
            """
        )

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.fetchall(
            """
            SELECT job_key, stage, status, message, created_at
            FROM pipeline_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    def list_jobs(
        self,
        *,
        stage: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = ["1=1"]
        params: list[Any] = []
        if stage:
            clauses.append("current_stage = ?")
            params.append(stage)
        if status:
            clauses.append("stage_status = ?")
            params.append(status)
        params.extend([limit, offset])
        where = " AND ".join(clauses)
        return self.fetchall(
            f"""
            SELECT *
            FROM pipeline_jobs
            WHERE {where}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        )

    def get_job_by_key(self, job_key: str) -> dict[str, Any] | None:
        return self.fetchone(
            "SELECT * FROM pipeline_jobs WHERE job_key = ?",
            (job_key,),
        )

    def events_for_job(self, job_key: str, limit: int = 50) -> list[dict[str, Any]]:
        return self.fetchall(
            """
            SELECT stage, status, message, created_at
            FROM pipeline_events
            WHERE job_key = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (job_key, limit),
        )

    def clear_all_jobs(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pipeline_events")
            conn.execute("DELETE FROM pipeline_jobs")
            conn.commit()
