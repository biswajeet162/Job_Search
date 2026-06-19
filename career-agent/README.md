# Career Agent — Raw HTML Fetcher

Visits **hard-coded career page URLs** from company JSON configs, captures full HTML, and stores results in **time-based, part-wise folders** (one JSON file per page).

Parsing structured job data is a **separate step** — use the saved HTML locally with Ollama or any parser.

## Folder layout

```
career-agent/
├── companies/              ← one JSON per company (you maintain these)
│   ├── mastercard.json
│   ├── visa.json
│   ├── uber.json
│   └── _schema.example.json
├── data/                   ← fetched HTML output (auto-created)
│   └── mastercard/
│       └── 14-06-2026/     ← date (DD-MM-YYYY)
│           └── 16-30-45/   ← time (HH-MM-SS) = one run
│               ├── manifest.json
│               ├── page_001.json
│               ├── page_002.json
│               └── ...
├── fetcher.py
├── storage.py
├── browser_controller.py
├── main.py
└── requirements.txt
```

## Company JSON format

Each file under `companies/` defines **what to fetch** and **when metadata** (schedule is informational — you trigger runs manually or via Task Scheduler):

```json
{
  "companyId": "mastercard",
  "companyName": "Mastercard",
  "jobPortalName": "Mastercard Careers Portal",
  "enabled": true,

  "schedule": {
    "intervalHours": 24,
    "notes": "Run once daily"
  },

  "fetchOptions": {
    "dismissCookies": true,
    "scrollBeforeCapture": true,
    "waitAfterLoadMs": 3000
  },

  "pages": [
    { "pageNumber": 1, "url": "https://careers.mastercard.com/us/en/search-results" },
    { "pageNumber": 2, "url": "https://careers.mastercard.com/us/en/search-results?from=5&s=1" },
    { "pageNumber": 3, "url": "https://careers.mastercard.com/us/en/search-results?from=10&s=1" }
  ]
}
```

**You provide every page URL directly** — no pagination clicking, no manual browser steps.

| Field | Required | Description |
|-------|----------|-------------|
| `companyId` | yes | Folder name under `data/` |
| `companyName` | yes | Display name |
| `jobPortalName` | no | Portal label stored in output |
| `enabled` | no | Skip if `false` (default: `true`) |
| `schedule` | no | Metadata (`intervalHours`, `notes`) |
| `fetchOptions` | no | Cookie dismiss, scroll, wait time |
| `pages` | yes | List of `{ pageNumber, url }` |

Copy `_schema.example.json` when adding a new company.

## Setup

### Option A — Conda (recommended)

```powershell
conda create -n job_search python=3.11 -y
conda activate job_search
cd career-agent
pip install -r requirements.txt
playwright install chromium
```

### Option B — venv

```powershell
cd career-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Run

```powershell
# Fetch Mastercard (7 hard-coded pages)
python main.py --company mastercard

# Fetch all enabled companies
python main.py --all

# Headless mode (testing)
python main.py --company mastercard --headless
```

Browser runs **visible by default** (`headless=False`).

## Output format

### Per-page file (`page_001.json`)

```json
{
  "companyId": "mastercard",
  "companyName": "Mastercard",
  "jobPortalName": "Mastercard Careers Portal",
  "pageNumber": 1,
  "url": "https://careers.mastercard.com/us/en/search-results",
  "scrapedAt": "2026-06-14T16:30:45+00:00",
  "status": "success",
  "title": "Search and Apply for Jobs at Mastercard",
  "finalUrl": "https://careers.mastercard.com/us/en/search-results",
  "htmlLength": 245000,
  "html": "<!DOCTYPE html>..."
}
```

### Run manifest (`manifest.json`)

```json
{
  "companyId": "mastercard",
  "companyName": "Mastercard",
  "runStartedAt": "2026-06-14T16:30:45+00:00",
  "runCompletedAt": "2026-06-14T16:32:10+00:00",
  "totalPages": 7,
  "successCount": 7,
  "failureCount": 0,
  "pages": [
    { "pageNumber": 1, "url": "...", "status": "success", "file": "page_001.json" }
  ]
}
```

## Next step: parse with Ollama (local)

This tool **only captures HTML**. To extract structured jobs:

1. Pick a run folder under `data/{company}/{date}/{time}/`
2. Feed each `page_XXX.json` → `html` field into Ollama locally
3. Shape the output however you need

The `llm/` module is kept for future parsing scripts if you want to add that next.

## Adding a new company

1. Copy `companies/_schema.example.json` → `companies/your_company.json`
2. Set `companyId`, names, and `enabled: true`
3. Add all page URLs with `pageNumber` (1, 2, 3 …)
4. Run: `python main.py --company your_company`
