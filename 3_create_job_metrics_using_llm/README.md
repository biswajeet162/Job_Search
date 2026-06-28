# Project 3 — Job Metrics (LLM)

Extracts structured metrics from project 2 detail JSON:

- **jobTitle**
- **description**
- **yearsOfExperience** (min / max / raw)
- **location**
- **skills** (full list)

## Setup

```bash
pip install -r requirements.txt
ollama pull llama3.1:8b
```

## Standalone

```bash
python main.py --detail-file ../2_get_job_details_using_job_link/job_details/00068588681-cognizant-*.json
python main.py --all --no-llm   # regex fallback without LLM
```

## Pipeline

Runs automatically via `pipeline/run_workers.py` (metrics-worker).

Output: `job_metrics/{jobId}-{company}-{timestamp}-metrics.json`
