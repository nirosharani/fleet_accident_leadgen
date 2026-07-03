# Fleet Accident Lead Generation System

A production-grade system that monitors Google News RSS feeds for fleet-related accidents involving major Indian companies. The pipeline collects articles, applies rule-based filtering, scores relevance, stores qualified incidents in SQLite, and exports them as CSV — turning raw news data into actionable sales leads.

---

## Project Overview

### Problem Statement

Fleet accidents — involving company-owned or employee transport vehicles — are a strong signal that a business may require new or replacement fleet services. Manually monitoring news sources for these events across hundreds of companies is impractical.

### Business Need

A lead generation system that automatically identifies fleet-related accidents involving target companies and delivers qualified, structured leads that a sales team can act on.

### Solution

This system ingests Google News RSS feeds using targeted search queries built from a company watchlist. Each article passes through a 7-step validation pipeline that checks for company mention, India context, transport and accident relevance, date freshness, and direct company involvement. Accepted incidents are scored, labeled with a confidence level, persisted to SQLite, and exported as CSV.

### Workflow

```
Company Watchlist → RSS Queries → Feed Fetching → Article Normalization
    → Duplicate Detection → 7-Step Validation → Scoring & Confidence
    → Database Persistence → CSV Export → Processing Report
```

---

## Features

- **Google News RSS Collection** — Automatically builds and fetches targeted RSS search queries for each watchlist company.
- **Company Watchlist** — 120+ major Indian companies across Pharma, FMCG, Manufacturing, and Services sectors.
- **Fleet Accident Detection** — Identifies articles involving employee transport, staff buses, company vehicles, and commercial fleet incidents.
- **Rule-based Filtering** — 7-step validation pipeline: target company detection, excluded company filtering, date validation, India context, transport context, accident context, and company involvement check.
- **SQLite Database** — Persistent storage for company master data, seen articles, accepted incidents, and rejected articles with WAL mode.
- **Duplicate Detection** — URL and URL-hash based deduplication across multiple RSS feeds and runs.
- **CSV Export** — Timestamped CSV files with 11 columns (Company, Sector, Headline, Score, Confidence, etc.).
- **Processing Reports** — Detailed execution summary written to both console and `logs/run_summary.log`.
- **CLI Options** — Configurable search window, company limit, dry-run mode, CSV toggle, custom output directory, and debug logging.
- **Automated Testing** — 126 unit tests covering filters, database, RSS scraper, CSV exporter, and utilities.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13+ |
| Database | SQLite 3 |
| RSS Parsing | feedparser |
| HTTP Client | requests |
| CSV Export | csv (stdlib) |
| CLI | argparse (stdlib) |
| Testing | unittest (stdlib) |
| Version Control | Git / GitHub |

---

## Project Structure

```
fleet_accident_leadgen/
├── main.py                 # CLI entry point, pipeline orchestrator
├── config.py               # Scoring values, keyword lists, constants
├── company_data.py         # Company watchlist (4 sectors, 120+ companies)
├── models.py               # Article and EvaluationResult dataclasses
├── logger.py               # Rotating file + console logger setup
├── database.py             # SQLite connection, schema, CRUD operations
├── rss_scraper.py          # RSS feed fetching, article normalization
├── filters.py              # Rule-based filtering and scoring engine
├── csv_exporter.py         # CSV export of accepted incidents
├── reporting.py            # Processing statistics and run summary
├── utils.py                # Hashing, URL cleaning, date parsing
├── requirements.txt        # Python package dependencies
├── README.md               # This file
├── .gitignore              # Git ignore rules
├── database/               # SQLite database files (gitignored)
├── logs/                   # Application logs (gitignored)
├── output/                 # CSV exports (gitignored)
└── tests/
    ├── __init__.py
    ├── test_filters.py     # FilterEngine validation pipeline tests
    ├── test_database.py    # DatabaseManager CRUD and edge case tests
    ├── test_utils.py       # Unit tests for utility functions
    ├── test_csv_exporter.py# CSV filename and export logic tests
    └── test_rss.py         # RSS scraper fetch and normalization tests
```

---

## Installation

### Prerequisites

- Python 3.13 or later
- Git

### Steps

```bash
# Clone the repository
git clone https://github.com/your-org/fleet_accident_leadgen.git
cd fleet_accident_leadgen

# Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS / Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

All configurable values are in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `FIRST_RUN_DAYS` | 7 | Search window in days for first run |
| `DAILY_LOOKBACK_HOURS` | 24 | Search window for subsequent daily runs |
| `MINIMUM_SCORE` | 60 | Minimum relevance score for acceptance |
| `RSS_TIMEOUT` | 10 | HTTP request timeout in seconds |
| `MAX_RETRIES` | 3 | RSS feed fetch retry count |
| `COMPANY_QUERY_LIMIT` | 10 | Max companies queried per run (0 = no limit) |

Scoring weights, keyword lists (positive, negative, transport, accident, fatality, involvement), Indian states and cities, and the RSS endpoint URL are also configurable in `config.py`.

The database is stored at `database/fleet.db`. CSV exports go to `output/` by default. Logs are written to `logs/fleet.log` with 5 MB rotating file handler and 3 backup files.

---

## Usage

### Basic Run

```bash
python main.py
```

Performs a first-run search across 7 days, processes all companies, stores results in SQLite, and exports accepted incidents to CSV.

### CLI Options

| Argument | Description |
|----------|-------------|
| `--days N` | Search window in N days (overrides auto-detection) |
| `--limit N` | Process only N companies (overrides `COMPANY_QUERY_LIMIT`) |
| `--dry-run` | Run the full pipeline without database writes or CSV export |
| `--no-export` | Skip CSV export even if accepted incidents exist |
| `--output-dir PATH` | Custom directory for CSV export |
| `--debug` | Enable verbose logging with stack traces |

### Examples

```bash
# Search last 7 days
python main.py --days 7

# Process only 5 companies
python main.py --limit 5

# Preview results without persisting anything
python main.py --dry-run

# Run pipeline but skip CSV export
python main.py --no-export

# Export CSV to a custom directory
python main.py --output-dir reports/

# Enable debug logging
python main.py --debug
```

### What Happens During a Run

1. Database is initialized and company master is seeded.
2. RSS search queries are generated from the company watchlist.
3. Google News RSS feeds are fetched with retry logic.
4. Articles are normalized, deduplicated, and validated through the 7-step filter pipeline.
5. Accepted incidents are scored and saved to the database.
6. CSV export is generated (unless skipped).
7. A detailed processing report is displayed and saved to `logs/run_summary.log`.

---

## Output

### SQLite Database (`database/fleet.db`)

Four tables:

| Table | Purpose |
|-------|---------|
| `company_master` | Watchlist companies by sector |
| `seen_articles` | Processed articles (URL + hash for deduplication) |
| `incident_records` | Accepted, scored incidents |
| `rejected_articles` | Rejected articles with rejection reason |

### CSV Exports (`output/fleet_incidents_YYYYMMDD_HHMMSS.csv`)

11 columns: Company, Sector, Headline, Summary, Incident Date, Source URL, Source Type, Score, Confidence, Outreach Hook, Created At.

### Logs

- `logs/fleet.log` — Rotating debug log (5 MB, 3 backups).
- `logs/run_summary.log` — Append-only execution summary with all pipeline metrics.

### Console Summary

After each run, a summary is printed with total articles, accepted, rejected, duplicates, database inserts, and execution time.

---

## Testing

```bash
python -m unittest
```

The test suite contains **126 automated tests** across 5 test files:

| File | Area |
|------|------|
| `tests/test_filters.py` | Company detection, validation pipeline, scoring, confidence |
| `tests/test_database.py` | Connection, table creation, CRUD, error handling |
| `tests/test_utils.py` | SHA-256, headline normalization, URL cleaning, date parsing |
| `tests/test_csv_exporter.py` | Filename generation, export logic, error handling |
| `tests/test_rss.py` | Feed fetching, retries, article normalization, deduplication |

All HTTP calls are mocked — no external network access is required during testing.

---

## Future Improvements

- Support additional news sources (Bing News, custom RSS feeds)
- Email notifications for high-confidence incidents
- Web dashboard for visualizing leads and filtering history
- Machine learning classification for improved accuracy
- Article full-text extraction for deeper context analysis
- Scheduled / automated execution with cron or Task Scheduler
- Multi-language support for regional news sources
