import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional

from company_data import WATCHLIST

logger = logging.getLogger(__name__)

_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")
_DB_PATH = os.path.join(_DB_DIR, "fleet.db")


class DatabaseManager:
    """Manages the SQLite database connection and schema."""

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Create the database directory, connect to SQLite, and enable
        :class:`sqlite3.Row` access so query results can be indexed by
        column name.
        """
        try:
            os.makedirs(_DB_DIR, exist_ok=True)
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA journal_mode=WAL")
            logger.info("Connected to database at %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("Failed to connect to database: %s", e)
            raise

    def close(self) -> None:
        """Close the database connection if open."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed.")

    def create_tables(self) -> None:
        """Create all required tables if they do not exist."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_master (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT UNIQUE NOT NULL,
                    sector TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    url_hash TEXT,
                    headline TEXT,
                    headline_hash TEXT,
                    company TEXT,
                    published_date TEXT,
                    processed_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incident_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT,
                    sector TEXT,
                    headline TEXT,
                    summary TEXT,
                    source_url TEXT,
                    source_type TEXT,
                    incident_date TEXT,
                    score INTEGER,
                    confidence TEXT,
                    outreach_hook TEXT,
                    created_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rejected_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    headline TEXT,
                    url TEXT,
                    company TEXT,
                    rejection_reason TEXT,
                    processed_at TEXT
                )
            """)

            self.connection.commit()
            logger.info("All database tables created successfully.")
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error("Failed to create tables: %s", e)
            raise

    def seed_company_master(self) -> int:
        """Insert all companies from WATCHLIST into company_master.

        Returns the total number of rows in company_master after seeding.
        """
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        inserted = 0
        try:
            cursor = self.connection.cursor()
            for sector, companies in WATCHLIST.items():
                for company_name in companies:
                    cursor.execute(
                        "INSERT OR IGNORE INTO company_master (company_name, sector) VALUES (?, ?)",
                        (company_name, sector),
                    )
                    if cursor.rowcount > 0:
                        inserted += 1
            self.connection.commit()
            logger.info("Seeded %d new companies into company_master.", inserted)
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error("Failed to seed company master: %s", e)
            raise

        cursor.execute("SELECT COUNT(*) FROM company_master")
        total = cursor.fetchone()[0]
        return total

    def is_first_run(self) -> bool:
        """Return True if incident_records is empty, otherwise False."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM incident_records")
            count = cursor.fetchone()[0]
            return count == 0
        except sqlite3.Error as e:
            logger.error("Failed to check first run: %s", e)
            raise

    def article_exists(self, url: str, url_hash: str) -> bool:
        """Return True if an article with the given URL or url_hash exists in seen_articles."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT 1 FROM seen_articles WHERE url = ? OR url_hash = ? LIMIT 1",
                (url, url_hash),
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error("Failed to check article existence: %s", e)
            raise

    def get_company_sector(self, company_name: str) -> Optional[str]:
        """Return the sector for the given company name, or None if not found."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT sector FROM company_master WHERE company_name = ?",
                (company_name,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error("Failed to get company sector: %s", e)
            raise

    def fetch_all_incidents(self) -> list[sqlite3.Row]:
        """Return all rows from incident_records as a list of sqlite3.Row objects.

        Each row provides column access by name (e.g. row["company"]).
        Returns an empty list if there are no incidents.
        """
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT company, sector, headline, summary,
                       incident_date, source_url, source_type,
                       score, confidence, outreach_hook, created_at
                FROM incident_records
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            logger.debug("Fetched %d incident records", len(rows))
            return rows
        except sqlite3.Error as e:
            logger.error("Failed to fetch incidents: %s", e)
            raise

    def save_seen_article(
        self,
        url: str,
        url_hash: str,
        headline: str,
        headline_hash: str,
        company: str,
        published_date: str,
    ) -> None:
        """Insert a processed article into seen_articles."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO seen_articles (url, url_hash, headline, headline_hash, company, published_date, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (url, url_hash, headline, headline_hash, company, published_date, datetime.now().isoformat()),
            )
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error("Failed to save seen article: %s", e)
            raise

    def save_incident(
        self,
        company: str,
        sector: str,
        headline: str,
        summary: str,
        source_url: str,
        source_type: str,
        incident_date: str,
        score: int,
        confidence: str,
        outreach_hook: str,
    ) -> None:
        """Insert a qualified incident into incident_records."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        now = datetime.now().isoformat()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO incident_records
                    (company, sector, headline, summary, source_url, source_type,
                     incident_date, score, confidence, outreach_hook, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (company, sector, headline, summary, source_url, source_type,
                 incident_date, score, confidence, outreach_hook, now),
            )
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error("Failed to save incident: %s", e)
            raise

    def save_rejection(
        self,
        headline: str,
        url: str,
        company: str,
        rejection_reason: str,
    ) -> None:
        """Insert a rejected article into rejected_articles."""
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")

        now = datetime.now().isoformat()
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO rejected_articles (headline, url, company, rejection_reason, processed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (headline, url, company, rejection_reason, now),
            )
            self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error("Failed to save rejection: %s", e)
            raise
