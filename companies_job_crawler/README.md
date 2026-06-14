# Job Crawler Engine

A production-oriented, modular Python service that continuously monitors company career pages, fetches job listings, and stores them as structured JSON files. It is designed as the **data collection layer** for a future AI-powered Job Intelligence Platform.

**Current scope:** crawling and storing jobs only.

**Not in scope (yet):** AI extraction, resume matching, embeddings, vector databases, notifications, PostgreSQL, Redis, or message queues.

---

## Table of Contents

- [What It Is](#what-it-is)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Data Storage](#data-storage)
- [Logging](#logging)
- [Testing](#testing)
- [What To Do](#what-to-do)
- [What NOT To Do](#what-not-to-do)
- [Future Extensions](#future-extensions)

---

## What It Is

The Job Crawler Engine is a **24x7 background service** built with FastAPI. It:

- Reads company definitions from a YAML file
- Runs a scheduler every minute to decide which crawlers should execute
- Dispatches crawlers concurrently using a thread pool
- Fetches and parses job listings from career pages
- Saves one JSON file per crawl execution (not one file per job)
- Logs every step with rotating log files
- Stores errors separately without stopping the service

The system is built so that future modules (AI processing, matching, notifications, databases) can be added **without rewriting the crawler core**.

---

## How It Works

### High-level flow

```
┌─────────────┐     every 60s      ┌──────────────────┐
│  APScheduler │ ────────────────► │  Scheduler Tick   │
└─────────────┘                    └─────────┬─────────┘
                                             │
                         for each enabled company in YAML
                                             │
                                             ▼
                              should run this minute?
                         (minute - offset) % interval == 0
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │  ThreadPoolExecutor      │
                              │  (non-blocking dispatch) │
                              └────────────┬─────────────┘
                                           │
                                           ▼
                              ┌──────────────────────────┐
                              │  CrawlService            │
                              │  → CompanyServiceRegistry│
                              │  → CompanyCrawlService   │
                              └────────────┬─────────────┘
                                           │
                         ┌─────────────────┴─────────────────┐
                         ▼                                   ▼
                 storage/{company}/...              errors/{company}/...
                   (success JSON)                     (failure JSON)
```

### Company-specific crawl pipeline

Every career site uses different field names and HTML/JSON structures. The engine handles this with **one dedicated module per company**, each containing three isolated components:

| Component | Responsibility | Example native fields |
|-----------|----------------|------------------------|
| **Fetcher** | Retrieve raw payload | HTTP HTML, future Playwright, API JSON |
| **Parser** | Extract jobs in the site's own shape | `requisitionId`, `work_id`, `roleTitle`, `jobDescription` |
| **Mapper** | Normalize to standard `Job` model | Maps to `job_id`, `job_title`, `job_url`; preserves full native dict in `raw_data` |

```
Company YAML entry
       │
       ▼
CompanyServiceRegistry.create(company)
       │
       ▼
┌──────────────────────────────────────────────┐
│  MastercardCrawlService  (example)           │
│    Fetcher  → raw HTML                       │
│    Parser   → [{requisitionId, jobTitle...}] │
│    Mapper   → Job(job_id, job_title, job_url)│
└──────────────────────────────────────────────┘
```

**Registered company modules:** `mastercard`, `visa`, `uber`  
**YAML-only companies:** use `GenericCompanyCrawlService` automatically

### Crawl lifecycle

Every company service follows the same lifecycle:

1. **`fetcher.fetch()`** — download raw data
2. **`parser.parse()`** — extract native job records (site-specific keys preserved)
3. **`mapper.map_many()`** — normalize to standard `Job` fields + `raw_data`
4. **`run()`** — orchestrate with retries, timing, and document assembly

### Scheduler timing formula

A company runs when:

```
(current_minute - offset_minutes) % interval_minutes == 0
```

Example with `interval_minutes: 15`:

| Company    | Offset | Runs at minutes        |
|-----------|--------|------------------------|
| Mastercard | 0      | :00, :15, :30, :45     |
| Visa       | 1      | :01, :16, :31, :46     |
| Uber       | 2      | :02, :17, :32, :47     |

Offsets stagger crawls so all companies do not hit the network at the same second.

### Failure handling

- Each crawl is wrapped in `try/except`
- Failures are logged and written to `errors/`
- One failed crawler **never** stops the scheduler or other crawlers
- Retries are configurable (default: 3 attempts with a short delay)

---

## Project Structure

```
companies_job_crawler/
├── app/
│   ├── main.py                 # FastAPI + Swagger (/docs, /redoc)
│   ├── dependencies.py         # Dependency injection container
│   ├── api/
│   │   ├── health.py           # GET /health
│   │   ├── scheduler.py        # Scheduler, companies, crawl, history
│   │   └── schemas.py          # OpenAPI response models
│   ├── companies/              # ★ One module per company
│   │   ├── base/               # Fetcher, Parser, Mapper, Service base classes
│   │   ├── generic/            # Fallback for YAML-only companies
│   │   ├── mastercard/service.py
│   │   ├── visa/service.py
│   │   ├── uber/service.py
│   │   └── registry.py         # CompanyServiceRegistry
│   ├── scheduler/
│   │   └── scheduler_service.py
│   ├── services/
│   │   ├── crawl_service.py    # Orchestrates company services
│   │   ├── storage_service.py  # JSON persistence + history
│   │   └── file_service.py     # Low-level file I/O
│   ├── models/                 # Pydantic models
│   ├── config/
│   │   ├── config_loader.py    # YAML loader
│   │   └── settings.py         # Paths and runtime settings
│   └── utils/
│       ├── logger.py           # Rotating file logging
│       ├── hash_util.py        # Job ID / execution ID helpers
│       └── datetime_util.py    # Folder and filename formatting
├── config/
│   └── companies.yaml          # All company + scheduler settings
├── storage/                    # Successful crawl JSON files
├── errors/                     # Failed crawl JSON files
├── logs/                       # Rotating application logs
├── tests/                      # Unit tests
└── requirements.txt
```

---

## Technology Stack

| Area          | Choice                          |
|---------------|---------------------------------|
| Language      | Python 3.12+                    |
| Web framework | FastAPI                         |
| Scheduling    | APScheduler                     |
| Concurrency   | ThreadPoolExecutor              |
| Configuration | YAML                            |
| HTTP          | requests (Playwright-ready)     |
| Parsing       | BeautifulSoup                   |
| Validation    | Pydantic                        |
| Storage       | JSON files                      |
| Logging       | Python logging + RotatingFileHandler |

---

## Getting Started

### Prerequisites

- Python **3.12 or newer**
- Internet access (crawlers fetch live career pages)

### 1. Install dependencies

From the project root:

```powershell
cd D:\ZZ_APPS\JOB_Search\companies_job_crawler
py -3.12 -m pip install -r requirements.txt
```

### 2. Review configuration

Edit `config/companies.yaml` if you want to change companies, intervals, or worker count.

### 3. Start the service

```powershell
py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On startup the service will:

1. Configure logging (`logs/job_crawler.log`)
2. Load `config/companies.yaml`
3. Start the background scheduler

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

| URL | Description |
|-----|-------------|
| `/docs` | **Swagger UI** — interactive API explorer |
| `/redoc` | ReDoc — alternative API documentation |
| `/openapi.json` | Raw OpenAPI 3 schema |

### 4. Verify it is running

```powershell
# Health check
curl http://localhost:8000/health

# Scheduler status
curl http://localhost:8000/scheduler/status

# Configured companies
curl http://localhost:8000/companies
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Trigger a manual crawl (optional)

```powershell
curl -X POST http://localhost:8000/crawler/mastercard
```

### 6. Run tests

```powershell
py -3.12 -m pytest tests/ -v
```

---

## Configuration

All company settings live in **`config/companies.yaml`**. No code changes are required to add a standard company.

### Example entry

```yaml
companies:
  - id: acme
    name: Acme Corp
    enabled: true
    interval_minutes: 15
    offset_minutes: 3
    crawler_type: html
    url: https://careers.acme.com
```

### Fields

| Field              | Description                                      |
|--------------------|--------------------------------------------------|
| `id`               | Unique identifier (used in paths and APIs)       |
| `name`             | Display name                                     |
| `enabled`          | `true` to schedule; `false` to skip              |
| `interval_minutes` | How often to crawl (in minutes)                  |
| `offset_minutes`   | Minute offset to stagger runs                    |
| `crawler_type`     | `html`, `playwright`, or future types            |
| `url`              | Career page URL                                  |

### Scheduler settings

```yaml
scheduler:
  max_workers: 5              # Thread pool size
  tick_interval_seconds: 60   # How often scheduler evaluates companies
```

After changing YAML, **restart the service** to reload configuration.

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Reference (Swagger)

| Method | Endpoint                    | Description                          |
|--------|-----------------------------|--------------------------------------|
| GET    | `/health`                   | Returns `{"status": "UP"}`           |
| GET    | `/scheduler/status`         | Scheduler running state and metadata |
| GET    | `/companies`                | All configured companies             |
| POST   | `/crawler/{company_id}`     | Trigger an immediate crawl           |
| GET    | `/history/{company_id}`     | Recent crawl history (`?limit=20`)   |

---

## Data Storage

### Successful crawls

Path pattern:

```
storage/{company_id}/{DD-MM-YYYY}/{HH-MM-SS}.json
```

Example:

```
storage/mastercard/14-06-2026/10-15-00.json
```

### JSON shape

Only three job fields are standardized. Everything else goes in `raw_data`:

```json
{
  "execution_id": "mastercard_20260614_101500",
  "company": {
    "id": "mastercard",
    "name": "Mastercard"
  },
  "crawler": {
    "started_at": "2026-06-14T10:15:00+00:00",
    "completed_at": "2026-06-14T10:15:12+00:00",
    "duration_ms": 12000,
    "status": "SUCCESS",
    "version": "1.0"
  },
  "statistics": {
    "total_jobs": 15
  },
  "jobs": [
    {
      "job_id": "mastercard_a1b2c3d4",
      "job_title": "Software Engineer",
      "job_url": "https://careers.mastercard.com/jobs/123",
      "raw_data": {
        "department": "Engineering"
      }
    }
  ]
}
```

### Failed crawls

```
errors/{company_id}/{DD-MM-YYYY}/{HH-MM-SS}.json
```

```json
{
  "execution_id": "mastercard_20260614_101500",
  "company": "mastercard",
  "timestamp": "2026-06-14T10:15:00+00:00",
  "error_type": "TimeoutError",
  "message": "Request timed out",
  "stacktrace": "..."
}
```

---

## Logging

Logs are written to **`logs/job_crawler.log`** with rotation (10 MB per file, 10 backups).

Format:

```
2026-06-14 10:15:00 INFO [mastercard_20260614_101500] [Mastercard] Mastercard crawler started
2026-06-14 10:15:10 INFO [mastercard_20260614_101500] [Mastercard] 15 jobs fetched
2026-06-14 10:15:11 INFO [mastercard_20260614_101500] [Mastercard] JSON file stored successfully
```

Logs include scheduler startup/shutdown, crawl start/completion, durations, job counts, retries, and exceptions.

---

## Testing

```powershell
py -3.12 -m pytest tests/ -v
```

Tests cover:

- Configuration loading
- Storage paths and JSON format
- Scheduler timing logic
- Crawler execution lifecycle
- Error handling (service never crashes)
- API smoke tests

---

## What To Do

### Operations

- **Run the service continuously** — it is designed for long-term 24x7 operation
- **Monitor `logs/job_crawler.log`** for errors and retry patterns
- **Check `errors/`** when a company repeatedly fails
- **Use `/scheduler/status`** and `/health` for uptime checks
- **Back up `storage/`** — this is your source-of-truth job archive
- **Restart after YAML changes** so new companies and intervals take effect

### Adding a new company (no code)

1. Add an entry to `config/companies.yaml`
2. Pick a unique `id`, set `url`, `interval_minutes`, and `offset_minutes`
3. Set `crawler_type: html` (or `playwright` when browser support is added)
4. Restart the service

The generic HTML crawler will extract job-like links automatically.

### Adding a company with custom page structure (recommended for production)

Each career site uses different IDs and field names. Create a dedicated module:

```
app/companies/acme/
  service.py    # wires Fetcher + Parser + Mapper
```

Inside `service.py`:

1. **`AcmeFetcher`** — how to retrieve data (HTTP, API, Playwright)
2. **`AcmeParser`** — extract native records (`work_id`, `job_description`, etc.)
3. **`AcmeJobMapper`** — map native keys → `job_id`, `job_title`, `job_url`
4. **`AcmeCrawlService`** — compose the three components
5. Register in `CompanyServiceRegistry._SERVICES["acme"] = AcmeCrawlService`

Use `FieldExtractor.first_present()` in mappers to handle multiple possible key names.

### Adding a new fetcher type (e.g. Workday API, Greenhouse)

1. Create a new `BaseJobFetcher` subclass in the company module
2. Wire it into that company's `CrawlService`
3. Set `crawler_type` in YAML for documentation purposes

---

## What NOT To Do

### Architecture and scope

- **Do not add AI, matching, or notifications inside company services** — they should only collect and preserve data
- **Do not normalize field names in the parser** — preserve native keys; mapping belongs in the Mapper
- **Do not share one parser/mapper across unrelated companies** — each site structure differs
- **Do not store one JSON file per job** — one file per execution keeps history manageable
- **Do not block the scheduler waiting for crawlers** — dispatch must stay non-blocking
- **Do not let one failure stop the whole service** — always catch, log, store error JSON, continue
- **Do not hardcode company URLs or intervals in Python** — use `config/companies.yaml`

### Configuration

- **Do not use duplicate company `id` values** — IDs are used in paths, APIs, and job hashes
- **Do not set `interval_minutes` to 0** — minimum is 1
- **Do not forget to restart** after editing YAML (config is loaded at startup and on scheduler ticks for dispatch, but structural changes are safest after restart)

### Data

- **Do not delete fields from `raw_data`** — future AI pipelines depend on preserved source information
- **Do not manually edit files in `storage/` while crawlers are running** — risk of inconsistent history
- **Do not commit secrets** (API keys, credentials) into YAML or the repo

### Crawling

- **Do not scrape aggressively** — respect site rate limits; use offsets and intervals
- **Do not assume HTTP is enough for every site** — many career pages need JavaScript (Playwright is the planned path)
- **Do not skip error investigation** — repeated `errors/` entries usually mean selectors or URLs need updating

### Development

- **Do not bypass `BaseCompanyCrawlService.run()`** — retries, timing, and document shape live there
- **Do not write files directly from company modules** — use `StorageService` via `CrawlService`
- **Do not disable tests before merging changes** — run `pytest` after modifications

---

## Future Extensions

The codebase is structured for these additions without major refactors:

| Future module        | Integration point                          |
|----------------------|--------------------------------------------|
| Playwright fetching  | Company-specific `Fetcher.fetch()`         |
| Workday / Greenhouse | New company module with API fetcher/parser |
| AI extraction        | New service reading `storage/` JSON        |
| PostgreSQL           | Replace or mirror `StorageService`         |
| Redis / queues       | Between scheduler and `CrawlService`       |
| Notifications        | Subscribe to crawl success/error events    |
| Embeddings / vectors | Downstream consumer of `raw_data`          |

Keep new features in **separate services**. The crawler engine should remain a reliable, dumb, durable data collector.

---

## Quick Troubleshooting

| Symptom                         | Likely cause                          | Action                                      |
|---------------------------------|---------------------------------------|---------------------------------------------|
| No JSON in `storage/`           | Company disabled or wrong minute      | Check YAML, wait for scheduled minute, or POST manual crawl |
| Empty `jobs` array              | Site uses JavaScript rendering        | Plan Playwright implementation              |
| Files in `errors/`              | Network timeout or HTML change        | Read error JSON stacktrace, update crawler  |
| Scheduler `running: false`    | Service not started or crashed        | Restart uvicorn, check logs                 |
| Config not updating             | Old process still running             | Restart the service                         |

---

## License

Internal project — Job Intelligence Platform data collection layer.
