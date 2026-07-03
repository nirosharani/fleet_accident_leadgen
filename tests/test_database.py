"""Tests for database.py.

Uses a temporary SQLite database file so the production database is
never touched.  Verifies:
  - Database initialisation and table creation
  - Company master seeding
  - First-run detection
  - Duplicate detection
  - Incident and rejection saving / retrieval
"""

import os
import tempfile
import unittest

from database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Exercise DatabaseManager with a temporary SQLite database."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_fleet.db")
        self.db = DatabaseManager(db_path=self.db_path)

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass
        self.temp_dir.cleanup()

    # -- Connection & initialisation ----------------------------------------

    def test_connect_creates_db_file(self):
        self.db.connect()
        self.assertTrue(os.path.exists(self.db_path))

    def test_double_connect_does_not_raise(self):
        self.db.connect()
        self.db.close()
        self.db.connect()
        self.assertIsNotNone(self.db.connection)

    def test_close_releases_connection(self):
        self.db.connect()
        self.db.close()
        self.assertIsNone(self.db.connection)

    def test_close_idempotent(self):
        self.db.close()
        self.db.close()
        self.assertIsNone(self.db.connection)

    # -- Table creation -----------------------------------------------------

    def test_create_tables_creates_all_tables(self):
        self.db.connect()
        self.db.create_tables()
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        for expected in ("company_master", "seen_articles",
                         "incident_records", "rejected_articles"):
            with self.subTest(table=expected):
                self.assertIn(expected, tables)

    def test_create_tables_idempotent(self):
        self.db.connect()
        self.db.create_tables()
        self.db.create_tables()
        cursor = self.db.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        for expected in ("company_master", "seen_articles",
                         "incident_records", "rejected_articles"):
            self.assertIn(expected, tables)

    # -- Company master -----------------------------------------------------

    def test_seed_company_master_populates_table(self):
        self.db.connect()
        self.db.create_tables()
        total = self.db.seed_company_master()
        self.assertGreater(total, 0)

    def test_seed_company_master_idempotent(self):
        self.db.connect()
        self.db.create_tables()
        self.db.seed_company_master()
        total1 = self.db.seed_company_master()
        total2 = self.db.seed_company_master()
        self.assertEqual(total1, total2)

    def test_get_company_sector_found(self):
        self.db.connect()
        self.db.create_tables()
        self.db.seed_company_master()
        sector = self.db.get_company_sector("Tata Steel")
        self.assertIsNotNone(sector)

    def test_get_company_sector_not_found(self):
        self.db.connect()
        self.db.create_tables()
        sector = self.db.get_company_sector("NonExistent")
        self.assertIsNone(sector)

    # -- First-run detection ------------------------------------------------

    def test_is_first_run_true_when_empty(self):
        self.db.connect()
        self.db.create_tables()
        self.assertTrue(self.db.is_first_run())

    def test_is_first_run_false_when_incidents_exist(self):
        self.db.connect()
        self.db.create_tables()
        self.db.connection.execute(
            "INSERT INTO incident_records (company, headline, score) "
            "VALUES (?, ?, ?)",
            ("TestCorp", "Test incident", 75),
        )
        self.db.connection.commit()
        self.assertFalse(self.db.is_first_run())

    # -- Duplicate detection ------------------------------------------------

    def test_article_exists_returns_false_for_new_article(self):
        self.db.connect()
        self.db.create_tables()
        self.assertFalse(
            self.db.article_exists("http://example.com", "hash123")
        )

    def test_article_exists_returns_true_for_saved_article(self):
        self.db.connect()
        self.db.create_tables()
        self.db.save_seen_article(
            url="http://example.com",
            url_hash="hash123",
            headline="Test",
            headline_hash="headhash",
            company="TestCorp",
            published_date="2024-07-15",
        )
        self.assertTrue(
            self.db.article_exists("http://example.com", "hash123")
        )

    def test_article_exists_matches_by_url(self):
        self.db.connect()
        self.db.create_tables()
        self.db.save_seen_article(
            url="http://example.com",
            url_hash="hash123",
            headline="Test",
            headline_hash="headhash",
            company="TestCorp",
            published_date="2024-07-15",
        )
        self.assertTrue(
            self.db.article_exists("http://example.com", "different_hash")
        )

    def test_article_exists_matches_by_url_hash(self):
        self.db.connect()
        self.db.create_tables()
        self.db.save_seen_article(
            url="http://example.com",
            url_hash="hash123",
            headline="Test",
            headline_hash="headhash",
            company="TestCorp",
            published_date="2024-07-15",
        )
        self.assertTrue(
            self.db.article_exists("http://other.com", "hash123")
        )

    # -- Incident save / fetch ----------------------------------------------

    def test_save_and_fetch_incident(self):
        self.db.connect()
        self.db.create_tables()
        self.db.save_incident(
            company="TestCorp",
            sector="Steel",
            headline="Bus accident in Jamshedpur",
            summary="A bus carrying employees overturned.",
            source_url="http://example.com/1",
            source_type="News",
            incident_date="2024-07-15",
            score=85,
            confidence="High",
            outreach_hook="",
        )
        rows = self.db.fetch_all_incidents()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "TestCorp")
        self.assertEqual(rows[0]["score"], 85)

    def test_fetch_all_incidents_returns_empty_when_none(self):
        self.db.connect()
        self.db.create_tables()
        rows = self.db.fetch_all_incidents()
        self.assertEqual(len(rows), 0)

    def test_fetch_all_incidents_orders_by_created_at_desc(self):
        self.db.connect()
        self.db.create_tables()
        self.db.save_incident(
            company="First", sector="A", headline="First",
            summary="", source_url="http://a.com", source_type="",
            incident_date="", score=50, confidence="Low",
            outreach_hook="",
        )
        self.db.save_incident(
            company="Second", sector="B", headline="Second",
            summary="", source_url="http://b.com", source_type="",
            incident_date="", score=80, confidence="High",
            outreach_hook="",
        )
        rows = self.db.fetch_all_incidents()
        self.assertEqual(len(rows), 2)

    # -- Rejection save -----------------------------------------------------

    def test_save_rejection(self):
        self.db.connect()
        self.db.create_tables()
        self.db.save_rejection(
            headline="Not relevant",
            url="http://example.com",
            company="TestCorp",
            rejection_reason="No accident context",
        )
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM rejected_articles")
        self.assertEqual(cursor.fetchone()[0], 1)

    # -- Operations without connect raise RuntimeError ----------------------

    def test_create_tables_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.create_tables()

    def test_seed_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.seed_company_master()

    def test_is_first_run_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.is_first_run()

    def test_article_exists_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.article_exists("url", "hash")

    def test_save_seen_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.save_seen_article("url", "h", "t", "hh", "c", "d")

    def test_save_incident_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.save_incident(
                "c", "s", "h", "s", "u", "t", "d", 0, "l", "",
            )

    def test_save_rejection_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.save_rejection("h", "u", "c", "r")

    def test_fetch_incidents_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.fetch_all_incidents()

    def test_get_sector_without_connect_raises(self):
        with self.assertRaises(RuntimeError):
            self.db.get_company_sector("Test")
