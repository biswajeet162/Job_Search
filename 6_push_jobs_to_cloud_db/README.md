# Project 6 — Push Jobs to Cloud DB

Pushes matched jobs + metrics to the cloud backend for user portal delivery.

## API (planned — `0_job_search_backend`)

```
POST /api/pipeline/jobs
{
  "jobKey": "cognizant:00068588681",
  "job": { ... job metrics ... },
  "matches": [ { "userId", "matchScore", "matchedSkills" } ]
}
```

## Pipeline

Runs via `pipeline` **push-worker**. If cloud API is unreachable, job is still marked complete locally (logged as warning).

## Status

Stub — implement when `0_job_search_backend` exists.

Configure API URL in `pipeline/config.json` → `cloud_api_base_url`.
