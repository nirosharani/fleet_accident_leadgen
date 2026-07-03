import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(errors="replace")

from logger import get_logger
from config import RSS_TIMEOUT, MAX_RETRIES
from company_data import WATCHLIST, EXCLUDED_COMPANIES
from database import DatabaseManager
from filters import FilterEngine
from models import EvaluationResult
from rss_scraper import RSSScraper
from csv_exporter import CSVExporter
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

    db.seed_company_master()
    first_run = db.is_first_run()

    cursor = db.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM company_master")
    company_total = cursor.fetchone()[0]

    print("Database initialized successfully.")
    print("Database schema verified.")
    print(f"Company master initialized successfully. ({company_total} companies loaded)")
    print(f"First run detected: {first_run}")
    print("Project ready.")
    print()

    # ---- First run / daily mode message ----
    if first_run:
        print("First run detected.")
        print("Searching previous 7 days.")
    else:
        print("Daily mode.")
        print("Searching previous 24 hours.")
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

    # ---- RSS Scraper ----
    print()
    print("--- RSS Scraper ---")
    scraper = RSSScraper()
    queries = scraper.generate_search_queries()
    print(f"Total search queries: {len(queries)}")

    articles = scraper.fetch_all()
    print(f"Total RSS feeds fetched: {len(scraper.search_urls)}")
    print(f"Total unique articles collected: {len(articles)}")

    if not articles:
        print()
        print("No articles to process.")
        db.close()
        return

    if articles:
        print()
        print("First 5 articles:")
        print("-" * 70)
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. Headline:      {article.title}")
            print(f"   Published Date: {article.published}")
            print(f"   Source URL:     {article.url}")
            print()

    # ---- Processing Pipeline ----
    print()
    print("--- Processing Pipeline ---")
    print()

    engine = FilterEngine()
    start_time = time.perf_counter()

    accepted_count = 0
    rejected_count = 0
    duplicate_count = 0
    db_inserts = 0

    for article in articles:
        url_hash = generate_sha256(article.url)
        headline_hash = generate_sha256(article.title)

        if db.article_exists(article.url, url_hash):
            duplicate_count += 1
            print(f"DUPLICATE | {article.title}")
            logger.info("Duplicate article skipped: %s", article.title)
            continue

        try:
            result = engine.evaluate_article(article, first_run=first_run)

            published_str = (
                article.published.isoformat() if article.published else ""
            )
            company = result.company or ""

            db.save_seen_article(
                article.url, url_hash, article.title, headline_hash,
                company, published_str,
            )
            db_inserts += 1

            if result.accepted:
                sector = db.get_company_sector(company) or ""
                db.save_incident(
                    company=company,
                    sector=sector,
                    headline=article.title,
                    summary=article.summary,
                    source_url=article.url,
                    source_type=article.source,
                    incident_date=published_str,
                    score=result.score,
                    confidence=result.confidence,
                    outreach_hook="",
                )
                db_inserts += 1
                accepted_count += 1
                print(f"ACCEPTED  | Score: {result.score} | {article.title}")
            else:
                db.save_rejection(
                    headline=article.title,
                    url=article.url,
                    company=company,
                    rejection_reason=result.reason or "",
                )
                db_inserts += 1
                rejected_count += 1
                print(f"REJECTED  | {result.reason} | {article.title}")

        except Exception as e:
            logger.error("Error processing article '%s': %s", article.title, e)
            print(f"ERROR     | {article.title}")
            continue

    elapsed = time.perf_counter() - start_time

    # ---- Summary ----
    print()
    print("=" * 39)
    print("SUMMARY")
    print("=" * 39)
    print(f"Total RSS Articles: {len(articles)}")
    print(f"Accepted:           {accepted_count}")
    print(f"Rejected:           {rejected_count}")
    print(f"Duplicates:         {duplicate_count}")
    print(f"Database Inserts:   {db_inserts}")
    print(f"Execution Time:     {elapsed:.2f}s")
    print("Execution Completed.")
    print()

    # ---- CSV Export ----
    print("--- CSV Export ---")
    file_path, export_count = CSVExporter.export_incidents(db)
    if export_count > 0:
        print(f"CSV Export Completed.")
        print(f"Exported Records: {export_count}")
        print(f"Output File: {file_path}")
    print()

    db.close()


if __name__ == "__main__":
    main()
