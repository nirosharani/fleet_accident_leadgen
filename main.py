import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(errors="replace")

from logger import get_logger
from database import DatabaseManager
from filters import FilterEngine
from rss_scraper import RSSScraper
from csv_exporter import CSVExporter
from reporting import ProcessingStats
from src.repositories.company_repository import CompanyRepository
from src.services.company_matcher import CompanyMatcher
from utils import (
    generate_sha256,
    normalize_headline,
    normalize_url,
    parse_article_date,
    is_within_date_range,
    build_google_rss_query,
    current_timestamp,
)

import csv_exporter as _csv_exporter
import filters as _filters
import rss_scraper as _rss_scraper

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments.

    Returns:
        An argparse.Namespace with fields:
            days, limit, dry_run, no_export, output_dir
    """
    parser = argparse.ArgumentParser(
        description="Fleet Accident Lead Generation System",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Search window in days (overrides first-run/daily-run logic)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of companies processed (overrides COMPANY_QUERY_LIMIT)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without database writes or CSV export",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip CSV export even if accepted incidents exist",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for CSV export",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging and stack traces",
    )
    return parser.parse_args()


def _setup_debug_logging(args: argparse.Namespace) -> None:
    """Enable debug-level logging on all handlers when --debug is passed."""
    if hasattr(args, "debug") and args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)


def _print_runtime_config(args: argparse.Namespace) -> None:
    """Display the effective runtime configuration."""
    days_display = (
        "Default (first-run/daily)" if args.days is None else str(args.days)
    )
    limit_display = (
        "Default" if args.limit is None else str(args.limit)
    )
    csv_status = "Disabled" if (args.no_export or args.dry_run) else "Enabled"
    out_dir = args.output_dir if args.output_dir else "output/"

    print("Runtime Configuration")
    print("---------------------")
    print(f"Days: {days_display}")
    print(f"Company Limit: {limit_display}")
    print(f"Dry Run: {args.dry_run}")
    print(f"CSV Export: {csv_status}")
    print(f"Output Directory: {out_dir}")
    print()


def _apply_runtime_overrides(args: argparse.Namespace) -> None:
    """Apply CLI argument overrides to module-level configuration values."""
    if args.days is not None:
        _filters.FIRST_RUN_DAYS = args.days

    if args.limit is not None:
        _rss_scraper.COMPANY_QUERY_LIMIT = args.limit

    if args.output_dir is not None:
        _csv_exporter._OUTPUT_DIR = os.path.abspath(args.output_dir)


def _initialize_database(
    args: argparse.Namespace,
) -> tuple:
    """Connect to the database, create tables, seed company master.

    Returns:
        A tuple of (DatabaseManager, first_run: bool, company_count: int).
    """
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

    if args.days is not None:
        first_run = True

    cursor = db.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM company_master")
    company_total = cursor.fetchone()[0]

    print("Database initialized successfully.")
    print("Database schema verified.")
    print(f"Company master initialized successfully. ({company_total} companies loaded)")
    print(f"First run detected: {first_run}")
    print("Project ready.")
    print()

    return db, first_run, company_total


def _print_run_mode(args: argparse.Namespace, first_run: bool) -> None:
    """Display the effective search mode (first-run / daily / custom days)."""
    if args.days is not None:
        print(f"Searching previous {args.days} days.")
    elif first_run:
        print("First run detected.")
        print("Searching previous 7 days.")
    else:
        print("Daily mode.")
        print("Searching previous 24 hours.")
    print()


def _run_utility_self_test() -> None:
    """Execute utility function self-test and display results."""
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


def _run_rss_scraper(stats: ProcessingStats) -> tuple:
    """Generate search queries, fetch all RSS feeds, and collect articles.

    Returns:
        A tuple of (RSSScraper instance, list of Article instances).
    """
    print()
    print("--- RSS Scraper ---")
    scraper = RSSScraper()
    queries = scraper.generate_search_queries()
    print(f"Total search queries: {len(queries)}")
    stats.set_queries_generated(len(queries))

    articles = scraper.fetch_all()
    print(f"Total RSS feeds fetched: {len(scraper.search_urls)}")
    stats.set_feeds_fetched(len(scraper.search_urls))
    print(f"Total unique articles collected: {len(articles)}")
    stats.set_articles_collected(len(articles))
    stats.set_unique_articles(len(articles))

    return scraper, articles


def _handle_empty_articles(stats: ProcessingStats, db: DatabaseManager) -> None:
    """Gracefully exit when no articles were collected."""
    print()
    print("No articles to process.")
    stats.set_csv_records_exported(0)
    stats.generate()
    db.close()


def _display_first_articles(articles: list) -> None:
    """Display the first 5 collected articles."""
    if not articles:
        return
    print()
    print("First 5 articles:")
    print("-" * 70)
    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. Headline:      {article.title}")
        print(f"   Published Date: {article.published}")
        print(f"   Source URL:     {article.url}")
        print()


def _process_articles(
    args: argparse.Namespace,
    articles: list,
    db: DatabaseManager,
    engine: FilterEngine,
    first_run: bool,
    stats: ProcessingStats,
) -> tuple:
    """Evaluate each article, write results to database, update counters.

    Returns:
        A tuple of (accepted_count, rejected_count, duplicate_count,
        db_inserts).
    """
    print()
    print("--- Processing Pipeline ---")
    print()

    accepted_count = 0
    rejected_count = 0
    duplicate_count = 0
    db_inserts = 0

    for article in articles:
        url_hash = generate_sha256(article.url)
        headline_hash = generate_sha256(article.title)

        if db.article_exists(article.url, url_hash):
            duplicate_count += 1
            stats.duplicate_skipped()
            print(f"DUPLICATE | {article.title}")
            logger.info("Duplicate article skipped: %s", article.title)
            continue

        try:
            result = engine.evaluate_article(article, first_run=first_run)

            published_str = (
                article.published.isoformat() if article.published else ""
            )
            company = result.company or ""

            if not args.dry_run:
                db.save_seen_article(
                    article.url, url_hash, article.title, headline_hash,
                    company, published_str,
                )
                db_inserts += 1

            if result.accepted:
                if not args.dry_run:
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
                stats.article_accepted()
                stats.incident_saved()
                print(f"ACCEPTED  | Score: {result.score} | {article.title}")
            else:
                if not args.dry_run:
                    db.save_rejection(
                        headline=article.title,
                        url=article.url,
                        company=company,
                        rejection_reason=result.reason or "",
                    )
                    db_inserts += 1
                rejected_count += 1
                stats.article_rejected()
                stats.rejection_saved()
                print(f"REJECTED  | {result.reason} | {article.title}")

        except Exception as e:
            logger.error("Error processing article '%s': %s", article.title, e)
            print(f"ERROR     | {article.title}")
            continue

    return accepted_count, rejected_count, duplicate_count, db_inserts


def _print_pipeline_summary(
    articles: list,
    accepted_count: int,
    rejected_count: int,
    duplicate_count: int,
    db_inserts: int,
    elapsed: float,
) -> None:
    """Print the post-pipeline summary to the console."""
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


def _handle_csv_export(
    args: argparse.Namespace,
    db: DatabaseManager,
    stats: ProcessingStats,
) -> None:
    """Export accepted incidents to CSV unless disabled by flags."""
    if not args.dry_run and not args.no_export:
        print("--- CSV Export ---")
        file_path, export_count = CSVExporter.export_incidents(db)
        if export_count > 0:
            print(f"CSV Export Completed.")
            print(f"Exported Records: {export_count}")
            print(f"Output File: {file_path}")
        stats.set_csv_records_exported(export_count)
    else:
        stats.set_csv_records_exported(0)


def main() -> None:
    """Parse arguments, apply overrides, initialise database, run pipeline."""
    args = parse_args()

    _setup_debug_logging(args)
    _print_runtime_config(args)
    _apply_runtime_overrides(args)

    db, first_run, _company_total = _initialize_database(args)

    stats = ProcessingStats()
    stats.start()

    _print_run_mode(args, first_run)

    _run_utility_self_test()

    _scraper, articles = _run_rss_scraper(stats)

    if not articles:
        _handle_empty_articles(stats, db)
        return

    _display_first_articles(articles)

    repo = CompanyRepository(db.connection)
    matcher = CompanyMatcher(repo)
    matcher.load_cache()
    engine = FilterEngine(company_matcher=matcher)
    pipeline_start = time.perf_counter()
    accepted, rejected, duplicates, inserts = _process_articles(
        args, articles, db, engine, first_run, stats,
    )
    pipeline_elapsed = time.perf_counter() - pipeline_start

    _print_pipeline_summary(
        articles, accepted, rejected, duplicates, inserts, pipeline_elapsed,
    )

    _handle_csv_export(args, db, stats)

    stats.generate()
    db.close()


def _main_entry() -> None:
    """Wrapper around main() that catches unexpected exceptions and logs them."""
    try:
        main()
    except Exception:
        import traceback
        logger.exception("Unhandled exception in pipeline: %s", traceback.format_exc())
        print()
        print("=" * 54)
        print("PIPELINE FAILED")
        print("=" * 54)
        print("An unexpected error occurred. Check logs/fleet.log for details.")
        print("Run with --debug to see the full error trace.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    _main_entry()
