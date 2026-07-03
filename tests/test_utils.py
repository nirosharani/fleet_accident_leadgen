"""Unit tests for utils.py.

Tests each utility function in isolation:
  - generate_sha256
  - normalize_headline
  - normalize_url
  - parse_article_date
  - is_within_date_range
  - build_google_rss_query
  - current_timestamp
"""

import unittest
from datetime import datetime, timezone, timedelta

from utils import (
    generate_sha256,
    normalize_headline,
    normalize_url,
    parse_article_date,
    is_within_date_range,
    build_google_rss_query,
    current_timestamp,
)


class TestGenerateSha256(unittest.TestCase):
    """Verify SHA-256 hashing behaviour."""

    def test_generates_64_char_hex(self):
        result = generate_sha256("Hello World")
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

    def test_strips_whitespace(self):
        self.assertEqual(
            generate_sha256("  Hello World  "),
            generate_sha256("Hello World"),
        )

    def test_empty_string(self):
        result = generate_sha256("")
        self.assertEqual(len(result), 64)

    def test_consistency(self):
        self.assertEqual(
            generate_sha256("test"),
            generate_sha256("test"),
        )

    def test_non_string_input_returns_hash_of_empty(self):
        result = generate_sha256(None)
        self.assertEqual(len(result), 64)

    def test_unicode_handling(self):
        result = generate_sha256("café")
        self.assertEqual(len(result), 64)


class TestNormalizeHeadline(unittest.TestCase):
    """Verify headline normalisation rules."""

    def test_lowercases(self):
        self.assertEqual(normalize_headline("Hello World"), "hello world")

    def test_removes_punctuation(self):
        self.assertEqual(
            normalize_headline("Tata Steel Bus Crash!!"),
            "tata steel bus crash",
        )

    def test_collapses_whitespace(self):
        self.assertEqual(
            normalize_headline("Hello    World"),
            "hello world",
        )

    def test_strips_whitespace(self):
        self.assertEqual(
            normalize_headline("  Hello World  "),
            "hello world",
        )

    def test_empty_string(self):
        self.assertEqual(normalize_headline(""), "")

    def test_handles_apostrophe(self):
        self.assertEqual(
            normalize_headline("Driver's death"),
            "drivers death",
        )


class TestNormalizeUrl(unittest.TestCase):
    """Verify URL tracking-parameter removal."""

    def test_removes_tracking_params(self):
        url = "https://example.com/news?foo=1&utm_source=twitter&gclid=abc"
        result = normalize_url(url)
        self.assertNotIn("utm_source", result)
        self.assertNotIn("gclid", result)
        self.assertIn("foo=1", result)

    def test_preserves_normal_urls(self):
        url = "https://example.com/news"
        self.assertEqual(normalize_url(url), url)

    def test_handles_empty_string(self):
        result = normalize_url("")
        self.assertIsInstance(result, str)

    def test_handles_malformed_url(self):
        result = normalize_url("not a url")
        self.assertIsInstance(result, str)

    def test_removes_multiple_tracking_params(self):
        url = ("https://example.com/page?"
               "utm_source=google&utm_medium=cpc&utm_campaign=spring"
               "&fbclid=xyz&gclid=abc&real_param=keep")
        result = normalize_url(url)
        self.assertNotIn("utm_source", result)
        self.assertNotIn("utm_medium", result)
        self.assertNotIn("utm_campaign", result)
        self.assertNotIn("fbclid", result)
        self.assertNotIn("gclid", result)
        self.assertIn("real_param=keep", result)

    def test_no_query_string_returned_unchanged(self):
        url = "https://example.com/news"
        self.assertEqual(normalize_url(url), url)


class TestParseArticleDate(unittest.TestCase):
    """Verify RSS date-string parsing."""

    def test_parses_rfc822(self):
        result = parse_article_date("Mon, 15 Jul 2024 12:00:00 GMT")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 7)
        self.assertEqual(result.day, 15)

    def test_parses_rfc822_with_tz_offset(self):
        result = parse_article_date("Mon, 15 Jul 2024 12:00:00 +0000")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)

    def test_parses_iso_format(self):
        result = parse_article_date("2024-07-15T12:00:00")
        self.assertIsNotNone(result)

    def test_parses_iso_with_z(self):
        result = parse_article_date("2024-07-15T12:00:00Z")
        self.assertIsNotNone(result)

    def test_parses_simple_date(self):
        result = parse_article_date("2024-07-15 12:00:00")
        self.assertIsNotNone(result)

    def test_returns_none_for_invalid_string(self):
        self.assertIsNone(parse_article_date("not a date"))

    def test_returns_none_for_empty_string(self):
        self.assertIsNone(parse_article_date(""))

    def test_returns_none_for_whitespace(self):
        self.assertIsNone(parse_article_date("   "))

    def test_returns_none_for_none(self):
        self.assertIsNone(parse_article_date(None))


class TestIsWithinDateRange(unittest.TestCase):
    """Verify date-range boundary logic."""

    def test_recent_date_within_range(self):
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        self.assertTrue(is_within_date_range(recent, 1))

    def test_old_date_outside_range(self):
        old = datetime.now(timezone.utc) - timedelta(days=10)
        self.assertFalse(is_within_date_range(old, 7))

    def test_exact_boundary_inclusive(self):
        ref = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        with unittest.mock.patch("utils.datetime") as mock_dt:
            mock_dt.now.return_value = ref + timedelta(days=7)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta
            self.assertTrue(is_within_date_range(ref, 7))

    def test_future_date_in_range(self):
        ref = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        with unittest.mock.patch("utils.datetime") as mock_dt:
            mock_dt.now.return_value = ref
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta
            self.assertTrue(is_within_date_range(ref + timedelta(days=1), 7))

    def test_zero_days_range(self):
        ref = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        with unittest.mock.patch("utils.datetime") as mock_dt:
            mock_dt.now.return_value = ref
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta
            self.assertTrue(is_within_date_range(ref, 0))

    def test_old_date_with_negative_days(self):
        ref = datetime(2024, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
        with unittest.mock.patch("utils.datetime") as mock_dt:
            mock_dt.now.return_value = ref
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta
            old = ref - timedelta(days=10)
            self.assertFalse(is_within_date_range(old, -1))


class TestBuildGoogleRssQuery(unittest.TestCase):
    """Verify RSS URL construction."""

    def test_builds_url_with_company_and_keyword(self):
        url = build_google_rss_query("Tata Steel", "bus accident")
        self.assertIn("q=Tata+Steel+bus+accident", url)
        self.assertTrue(url.startswith("https://news.google.com/rss/search"))

    def test_builds_url_with_empty_company(self):
        url = build_google_rss_query("", "accident")
        self.assertIn("q=", url)

    def test_encodes_special_characters(self):
        url = build_google_rss_query("Company & Co", "crash")
        self.assertIn("Company+%26+Co", url)


class TestCurrentTimestamp(unittest.TestCase):
    """Verify timestamp format."""

    def test_returns_iso_format_string(self):
        ts = current_timestamp()
        self.assertIsInstance(ts, str)
        self.assertIn("T", ts)

    def test_returns_utc_timezone_aware(self):
        ts = current_timestamp()
        parsed = datetime.fromisoformat(ts)
        self.assertIsNotNone(parsed.tzinfo)
