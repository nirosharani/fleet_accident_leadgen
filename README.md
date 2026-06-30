# Fleet Accident Lead Generation System

A production-grade system that monitors RSS feeds and Google News for fleet-related accidents involving major Indian companies, generating qualified sales leads.

## Folder Structure

```
fleet_accident_leadgen/
├── main.py              # Entry point
├── config.py            # Configuration constants
├── company_data.py      # Company watchlist by sector
├── models.py            # Data models (dataclasses)
├── logger.py            # Reusable logger
├── requirements.txt     # Dependencies
├── README.md            # This file
├── database/            # SQLite database (future)
├── logs/                # Application logs
└── output/              # CSV exports (future)
```

## Installation

```bash
pip install -r requirements.txt
```

## How to Run

```bash
python main.py
```

## Future Roadmap

- RSS feed scraping from Google News
- Article parsing and keyword matching
- Scoring and filtering of incidents
- SQLite persistence of incidents and rejected articles
- CSV export of qualified leads
- Scheduling and automation support
