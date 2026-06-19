# Direct Job Scraper

Extracts **structured job listings** (title + URL) directly from career pages using **CSS selectors** and **pagination clicking**. Separate from `career-agent/` which captures raw HTML.

## How it works

```
companies/mastercard.json  →  Playwright opens career URL
                            →  Apply filters (location, sort, etc.)
                            →  Scrape up to maxPages
                            →  Extract job links via CSS selectors
                            →  Click "Next" until limit or end
                            →  Save structured JSON to output/
```

## Folder layout

```
direct_job_scraper/
├── companies/           ← selector-based configs
│   ├── mastercard.json
│   └── _schema.example.json
├── output/              ← extracted jobs
│   ├── mastercard_jobs.json              ← latest snapshot
│   └── mastercard/19-06-2026/02-40-04.json  ← run history
├── agent.py
├── browser_controller.py
├── storage.py
├── main.py
└── requirements.txt
```

## Setup

Uses the same conda env as career-agent:

```powershell
conda activate job_search
cd D:\ZZ_APPS\JOB_Search\direct_job_scraper
pip install -r requirements.txt
playwright install chromium
```

## Run

```powershell
python main.py --company mastercard
python main.py --company mastercard --visible   # show browser window
python main.py --all
```

## Company config

Each company JSON has these sections:

| Section | Purpose |
|---------|---------|
| `steps` | Open URL, dismiss cookies (setup before filters) |
| `filters` | Location, sort, experience — applied **before** scraping |
| `scrapeOptions` | `maxPages`, wait times, scroll behaviour |
| `jobLinkStrategy` | How to extract job links from the page |
| `pagination` | Next-button selector |

### Example (`mastercard.json`)

```json
{
  "companyName": "Mastercard",
  "careerUrl": "https://careers.mastercard.com/us/en/search-results",
  "enabled": true,
  "defaultLocation": "India",

  "steps": [
    { "action": "open_url" },
    { "action": "dismiss_cookies" }
  ],

  "filters": [
    {
      "id": "location",
      "label": "Location",
      "action": "autocomplete",
      "inputSelector": "input[placeholder*='Location']",
      "value": "India",
      "optionText": "India",
      "optional": false
    },
    {
      "id": "sortBy",
      "label": "Sort by most recent",
      "action": "select",
      "selector": "select[aria-label*='Sort']",
      "value": "Most recent",
      "matchBy": "label",
      "optional": true
    }
  ],

  "scrapeOptions": {
    "maxPages": 2,
    "waitAfterFiltersMs": 2500,
    "scrollBeforeExtract": true,
    "waitForResultsSelector": "a[href*='/job/']"
  },

  "jobLinkStrategy": {
    "type": "direct_extract",
    "linkSelector": "a[href*='/job/']"
  },

  "pagination": {
    "type": "next_button",
    "selector": "a[aria-label='View next page']"
  }
}
```

### Filter actions

| Action | Required fields | Description |
|--------|-----------------|-------------|
| `facet_pick` | `openSelector`, `inputSelector`, `value`, `optionSelector` | Facet panel: open → search → pick |
| `autocomplete` | `inputSelector`, `value` | Type and pick a suggestion |
| `select` | `selector`, `value` | Native `<select>` dropdown |
| `fill` | `selector`, `value` | Text input + Enter |
| `click_option` | `openSelector`, `optionSelector` | Custom dropdown |
| `click` | `selector` | Click a filter button |

All filters support `"optional": true` to skip on failure.

### scrapeOptions

| Field | Default | Description |
|-------|---------|-------------|
| `maxPages` | unlimited | Stop after N pages (e.g. `2`) |
| `waitAfterFiltersMs` | `0` | Pause after filters apply |
| `scrollBeforeExtract` | `true` | Scroll before extracting links |
| `waitForResultsSelector` | — | Wait for jobs to appear |

### Step actions

| Action | Fields |
|--------|--------|
| `open_url` | `url` (optional) |
| `dismiss_cookies` | — |
| `apply_filter` | `selector`, `value` |
| `click` | `selector` |
| `scroll` | — |
| `wait_for` | `selector` (optional, non-fatal if missing) |
| `screenshot` | — |

### Job link strategies

- `direct_extract` — `linkSelector` or `jobCardSelector`
- `hover_and_extract` — `jobCardSelector` + `linkSelector`

## Output format

```json
{
  "company": "Mastercard",
  "careerUrl": "https://careers.mastercard.com/...",
  "totalJobs": 10,
  "pagesScraped": 2,
  "maxPages": 2,
  "filtersApplied": [
    { "id": "location", "label": "Location", "value": "India" },
    { "id": "sortBy", "label": "Sort by most recent", "value": "Most recent" }
  ],
  "scrapedAt": "2026-06-19T...",
  "jobs": [
    {
      "company": "Mastercard",
      "jobTitle": "Software Engineer",
      "jobUrl": "https://...",
      "location": "",
      "pageNumber": 1,
      "scrapedAt": "..."
    }
  ]
}
```

## vs career-agent

| | `direct_job_scraper/` | `career-agent/` |
|---|---|---|
| **Input** | CSS selectors + pagination | Hard-coded page URLs |
| **Output** | Parsed jobs (title, URL) | Raw HTML per page |
| **Parsing** | In-browser, rule-based | You parse with Ollama later |
| **Best for** | Stable sites with good selectors | Full control, any site |
