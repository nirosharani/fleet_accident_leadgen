import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger
from config import (
    FIRST_RUN_DAYS,
    DAILY_LOOKBACK_HOURS,
    MINIMUM_SCORE,
    RSS_TIMEOUT,
    MAX_RETRIES,
    MAX_RESULTS_PER_RUN,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS,
    EXCLUDED_COMPANIES as CONFIG_EXCLUDED,
)
from company_data import WATCHLIST, EXCLUDED_COMPANIES
from database import DatabaseManager
from utils import (
    generate_sha256,
    normalize_headline,
    normalize_url,
    parse_article_date,
    is_within_date_range,
    build_google_rss_query,
    current_timestamp,
)

logger = get_logger(__name__)


def main() -> None:
    print("=" * 54)
    print("Fleet Accident Lead Generation System")
    print("=" * 54)
    print()
    logger.info("Initializing logger.")
    logger.info("Configuration loaded.")
    logger.info("Company watchlist loaded.")

    db = DatabaseManager()
    db.connect()
    db.create_tables()

    count = db.seed_company_master()
    first_run = db.is_first_run()
    db.close()

    print("Database initialized successfully.")
    print("Database schema verified.")
    print(f"Company master initialized successfully. ({count} companies loaded)")
    print(f"First run detected: {first_run}")
    print("Project ready.")
    print()

    # ---- Utility self-test ----
    print("--- Utility Self-Test ---")
    sha = generate_sha256("  Hello World  ")
    print(f"SHA-256 generated: {sha}")

    norm = normalize_headline("Tata Steel Bus Crash!!  ")
    print(f"Headline normalized: {norm}")

    clean_url = normalize_url(
        "https://example.com/news?foo=1&utm_source=twitter&gclid=abc"
    )
    print(f"URL normalized: {clean_url}")

    parsed = parse_article_date("Mon, 15 Jul 2024 12:00:00 GMT")
    print(f"Date parsed: {parsed}")

    in_range = is_within_date_range(parsed, 365)
    print(f"Date within 365 days: {in_range}")

    rss_url = build_google_rss_query("Tata Steel", "bus accident")
    print(f"RSS URL generated: {rss_url}")

    ts = current_timestamp()
    print(f"Timestamp created: {ts}")


if __name__ == "__main__":
    main()
