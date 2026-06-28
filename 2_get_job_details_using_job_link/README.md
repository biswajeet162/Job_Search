# Get Job Details Using Job Link

Scrapes **full job detail pages** for every entry in project 1's `final_job_list.json`.

## Input

`../1_scrape_job_careers_pages/jobs_dashboard/final_job_list.json`

## Output

| Path | Description |
|------|-------------|
| `job_details/{jobId}-{company}-{timestamp}.json` | One file per scraped job |
| `job_details_index.json` | Index of all detail files |
| `scraped_registry.json` | Tracks scraped jobs (skip on re-run) |

## Setup

```bash
cd 2_get_job_details_using_job_link
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Scrape all new jobs (skips already scraped)
python main.py

# First 5 new jobs only
python main.py --limit 5

# One company
python main.py --company Cognizant --limit 10

# Re-scrape everything
python main.py --force

# Show browser window
python main.py --visible --limit 1
```

## Extraction strategy

1. **API** — SmartRecruiters, Greenhouse (no browser)
2. **JSON-LD** — `JobPosting` schema on the page
3. **Company config** — `company_configs/{company}.json`
4. **Generic DOM** — common title/description selectors

Each output JSON includes `sourceJob` (from the list), `details` (title, description, location, etc.), and `extractionMethod`.
