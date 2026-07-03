"""Tests for csv_exporter.py.

Verifies:
  - CSV filename format
  - Export with no data (empty database)
  - Export with data writes correct content
  - Error handling for write failures
"""

import csv
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from csv_exporter import CSVExporter


class TestCSVExporterBuildFilename(unittest.TestCase):
    """Verify timestamped filename generation."""

    def test_filename_starts_with_prefix(self):
        name = CSVExporter._build_filename()
        self.assertTrue(name.startswith("fleet_incidents_"))

    def test_filename_ends_with_csv(self):
        name = CSVExporter._build_filename()
        self.assertTrue(name.endswith(".csv"))

    def test_filename_contains_timestamp(self):
        name = CSVExporter._build_filename()
        self.assertIn("_", name.split(".")[0])


class TestCSVExporterExportIncidents(unittest.TestCase):
    """Verify export logic with mocked database and temporary directory."""

    def test_export_no_incidents_returns_empty_path(self):
        mock_db = MagicMock()
        mock_db.fetch_all_incidents.return_value = []

        path, count = CSVExporter.export_incidents(mock_db)
        self.assertEqual(path, "")
        self.assertEqual(count, 0)

    def test_export_with_incidents_creates_file(self):
        mock_db = MagicMock()
        mock_db.fetch_all_incidents.return_value = [
            dict(
                company="TestCorp",
                sector="Steel",
                headline="Test accident",
                summary="Summary text",
                source_url="http://example.com",
                source_type="News",
                incident_date="2024-07-15",
                score=85,
                confidence="High",
                outreach_hook="",
                created_at="2024-07-15T12:00:00",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("csv_exporter._OUTPUT_DIR", tmpdir):
                path, count = CSVExporter.export_incidents(mock_db)

            self.assertEqual(count, 1)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(path.endswith(".csv"))

    def test_export_csv_content_is_correct(self):
        row_data = dict(
            company="TestCorp",
            sector="Steel",
            headline="Test accident",
            summary="Summary text",
            source_url="http://example.com",
            source_type="News",
            incident_date="2024-07-15",
            score=85,
            confidence="High",
            outreach_hook="",
            created_at="2024-07-15T12:00:00",
        )
        mock_db = MagicMock()
        mock_db.fetch_all_incidents.return_value = [
            row_data,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("csv_exporter._OUTPUT_DIR", tmpdir):
                path, count = CSVExporter.export_incidents(mock_db)

            with open(path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

        self.assertEqual(len(rows), 1)
        header_map = {
            "company": "Company", "sector": "Sector",
            "headline": "Headline", "summary": "Summary",
            "source_url": "Source URL", "source_type": "Source Type",
            "incident_date": "Incident Date", "score": "Score",
            "confidence": "Confidence", "outreach_hook": "Outreach Hook",
            "created_at": "Created At",
        }
        for key, value in row_data.items():
            col = header_map[key]
            self.assertEqual(str(rows[0][col]), str(value))

    def test_export_empty_db_no_file_created(self):
        mock_db = MagicMock()
        mock_db.fetch_all_incidents.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("csv_exporter._OUTPUT_DIR", tmpdir):
                path, count = CSVExporter.export_incidents(mock_db)

            self.assertEqual(path, "")
            self.assertEqual(count, 0)
            self.assertEqual(len(os.listdir(tmpdir)), 0)

    def test_write_failure_raises_os_error(self):
        mock_db = MagicMock()
        mock_db.fetch_all_incidents.return_value = [
            dict(
                company="TestCorp", sector="", headline="",
                summary="", source_url="", source_type="",
                incident_date="", score=0, confidence="",
                outreach_hook="", created_at="",
            ),
        ]

        with patch("csv_exporter.os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = OSError("Permission denied")
            with self.assertRaises(OSError):
                CSVExporter.export_incidents(mock_db)
