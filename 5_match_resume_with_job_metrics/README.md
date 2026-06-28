# Project 5 — Match Resume with Job Metrics

Scores each job against each resume using skills overlap (extensible to semantic LLM matching).

## Input

- `3_create_job_metrics_using_llm/job_metrics/*.json`
- `4_create_resume_metrics_using_llm/resume_metrics/*.json`

## Output

- `5_match_resume_with_job_metrics/matches/{jobId}-{company}-{time}-matches.json`

## Pipeline

Runs via `pipeline` **match-worker** automatically after job metrics stage.

## Status

Basic skill-overlap matching implemented in `pipeline/workers/match_worker.py`.
Upgrade to LLM semantic matching in a future phase.
