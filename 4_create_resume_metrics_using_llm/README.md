# Project 4 — Resume Metrics (LLM)

Extracts structured metrics from user-uploaded resumes:

- **yearsOfExperience**
- **preferredLocations**
- **certifications**
- **skills**

## Flow

1. Cloud backend receives resume upload from `0_job_search_frontend_cloud`
2. Resume file lands in `resume_inbox/` (or webhook triggers local worker)
3. LLM extracts metrics → `resume_metrics/{userId}-{timestamp}-metrics.json`
4. Pipeline `resume_pipeline` table updated

## Status

Stub — implement when cloud backend + resume upload is wired.

## Metrics schema

See `ARCHITECTURE.md` → Resume metrics schema.
