RUn inside  Conda ENV

job_search


# Direct Job Scraper

Extracts **structured job listings** from career pages using **per-company JSON configs**. The Python engine is generic; each company defines its own selectors, filters, pagination, and job ID rules in `companies/<name>.json`.

## Architecture

```
companies/citi.json          ← all company-specific rules
companies/mastercard.json
        ↓
company_config.py            ← load + validate config
extraction.py                ← generic strategy dispatch
browser_controller.py        ← Playwright primitives
agent.py                     ← orchestration loop
        ↓
        output/<company>/{DD_MM_YYYY}/{serial}_{HH}-{MM}-{SS}.json
```

**Rule:** nothing company-specific in Python. Add a new company by adding a JSON file.

## Folder layout

```
direct_job_scraper/
├── companies/           ← one JSON per company (the only place to edit for new sites)
│   ├── citi.json
│   ├── cognizant.json
│   ├── nagarro.json
│   ├── mastercard.json
│   └── _schema.example.json
├── company_config.py    ← config validation
├── extraction.py        ← job extraction strategies
├── job_id_util.py       ← job ID resolution from config
├── agent.py
├── browser_controller.py
├── main.py
└── output/
    └── citi/
        └── 19_06_2026/
            ├── 1_20-23-56.json
            └── 2_21-05-12.json

## Setup

```powershell
conda activate job_search
cd D:\ZZ_APPS\JOB_Search\direct_job_scraper
pip install -r requirements.txt
playwright install chromium
```

## Run

```powershell
python main.py --company citi
python main.py --company cognizant
python main.py --company nagarro
python main.py --company mastercard
python main.py --all
python main.py --company citi --visible   # show browser
```

## Company config sections

| Section | Purpose |
|---------|---------|
| `steps` | Pre-scrape setup (open URL, dismiss overlays) |
| `filters` | Location, country, sort — applied before scraping |
| `scrapeOptions` | `maxPages`, waits, scroll behaviour |
| `jobLinkStrategy` | Extraction strategy + selectors + **jobId rules** |
| `pagination` | `next_button` or `page_jump` |

See `companies/_schema.example.json` for a full annotated template.

### Job ID rules (`jobLinkStrategy.jobId`)

Each company defines how to get a stable job ID:

```json
"jobId": {
  "source": "url",
  "urlPattern": "/job/(R-\\d+)/"
}
```

```json
"jobId": {
  "source": "attribute_first",
  "attribute": "data-job-id",
  "attributeScope": "link",
  "urlPattern": "/(\\d+)$"
}
```

| `source` | Behaviour |
|----------|-----------|
| `url` | Regex on job URL only |
| `attribute` | HTML attribute only (`data-job-id`, etc.) |
| `attribute_first` | Try attribute, fall back to URL pattern |
| `url_first` | Try URL pattern, fall back to attribute |

### Extraction strategies (`jobLinkStrategy.type`)

| Type | When to use | Required config |
|------|-------------|-----------------|
| `direct_extract` | Simple link lists | `linkSelector`, `jobId` |
| `card_extract` | Structured job cards | `cardSelector`, `linkSelector`, `fields`, `jobId` |
| `hover_and_extract` | Links appear on hover | `jobCardSelector`, `linkSelector`, `jobId` |

`fields` maps output keys to CSS selectors **relative to each card**:

```json
"fields": {
  "location": "span.sr-job-location",
  "jobType": "span.sr-job-type"
}
```

### Filter actions

| Action | Required fields |
|--------|-----------------|
| `facet_pick` | `openSelector`, `inputSelector`, `value`, `optionSelector` |
| `autocomplete` | `inputSelector`, `value` |
| `select` | `selector`, `value` |
| `checkbox` | `checkboxSelector` (+ optional `openSelector`) |
| `click_option` | `openSelector`, `optionSelector` |
| `fill` | `selector`, `value` |
| `click` | `selector` |

### Pagination types

| Type | Config |
|------|--------|
| `next_button` | `selector` — click Next between pages |
| `page_jump` | `inputSelector`, `goButtonSelector` — fill page number + Go |
| `none` | Single page — no pagination (all jobs on one load) |

## Adding a new company

1. Copy `companies/_schema.example.json` → `companies/acme.json`
2. Set `careerUrl`, filters, selectors from DevTools
3. Define `jobLinkStrategy.jobId` with the right `urlPattern` or `attribute`
4. Run: `python main.py --company acme`

## Output format

```json
{
  "company": "Citi",
  "totalJobs": 30,
  "pagesScraped": 2,
  "jobs": [
    {
      "company": "Citi",
      "jobId": "79221015312",
      "jobTitle": "Asset Servicing Intmd Analyst",
      "jobUrl": "https://jobs.citi.com/job/...",
      "location": "Pune, Maharashtra, India",
      "jobType": "Hybrid",
      "pageNumber": 1,
      "scrapedAt": "..."
    }
  ]
}
```

## vs career-agent

| | `direct_job_scraper/` | `career-agent/` |
|---|---|---|
| **Config** | Selectors + strategies per JSON | Hard-coded page URLs |
| **Output** | Structured jobs immediately | Raw HTML for later parsing |
| **Best for** | Sites with stable CSS/DOM | Any site, LLM parsing later |
