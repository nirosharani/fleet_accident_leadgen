"""Tests for rss_scraper.py.

All HTTP requests are mocked so that no external network calls are made
during unit tests.  Verifies:
  - Successful feed parsing
  - Empty feed handling
  - Invalid / bozo feed handling
  - Timeout handling with retries
  - Article normalisation
  - Deduplication across feeds
"""

import unittest
from unittest.mock import patch, Mock, MagicMock

from rss_scraper import RSSScraper


class TestRSSScraperFetchFeed(unittest.TestCase):
    """Exercise RSS feed fetching with mocked HTTP and feedparser."""

    def setUp(self):
        self.scraper = RSSScraper()

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.content = b"<rss><item><title>T</title></item></rss>"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        with patch("rss_scraper.feedparser.parse") as mock_parse:
            mock_parse.return_value.entries = [
                {"title": "Article 1", "link": "http://example.com/1"}
            ]
            mock_parse.return_value.bozo = False
            entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 1)

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_empty_response(self, mock_get):
        mock_resp = Mock()
        mock_resp.content = b""
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        with patch("rss_scraper.feedparser.parse") as mock_parse:
            mock_parse.return_value.entries = []
            mock_parse.return_value.bozo = False
            entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 0)

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_timeout_retries_then_returns_empty(self, mock_get):
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Connection timed out")

        entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 0)
        self.assertEqual(mock_get.call_count, 3)

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_http_error_retries_then_returns_empty(self, mock_get):
        from requests.exceptions import HTTPError
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = HTTPError("404")
        mock_get.return_value = mock_resp

        entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 0)
        self.assertEqual(mock_get.call_count, 3)

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_request_exception_retries(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("Connection refused")

        entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 0)
        self.assertEqual(mock_get.call_count, 3)

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_bozo_without_entries_retries(self, mock_get):
        mock_resp = Mock()
        mock_resp.content = b"invalid xml"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        with patch("rss_scraper.feedparser.parse") as mock_parse:
            mock_parse.return_value.entries = []
            mock_parse.return_value.bozo = True
            mock_parse.return_value.bozo_exception = Exception("Parse error")
            entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 0)

    @patch("rss_scraper.requests.get")
    def test_fetch_feed_bozo_with_entries_succeeds(self, mock_get):
        mock_resp = Mock()
        mock_resp.content = b"<rss><item><title>T</title></item></rss>"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        with patch("rss_scraper.feedparser.parse") as mock_parse:
            mock_parse.return_value.entries = [
                {"title": "Art", "link": "http://ex.com"}
            ]
            mock_parse.return_value.bozo = True
            mock_parse.return_value.bozo_exception = Exception("Minor issue")
            entries = self.scraper.fetch_feed("http://example.com/rss")

        self.assertEqual(len(entries), 1)


class TestRSSScraperNormalizeArticle(unittest.TestCase):
    """Verify feed entry → Article conversion."""

    def setUp(self):
        self.scraper = RSSScraper()

    def test_normalize_valid_entry(self):
        entry = {
            "title": "Test Article",
            "link": "http://example.com/news?utm_source=twitter",
            "published": "Mon, 15 Jul 2024 12:00:00 GMT",
            "summary": "A summary of the event.",
            "source": MagicMock(title="News Source"),
        }
        article = self.scraper.normalize_article(entry)
        self.assertIsNotNone(article)
        self.assertEqual(article.title, "Test Article")
        self.assertNotIn("utm_source", article.url)
        self.assertEqual(article.source, "News Source")

    def test_normalize_empty_title_and_link_returns_none(self):
        entry = {"title": "", "link": ""}
        article = self.scraper.normalize_article(entry)
        self.assertIsNone(article)

    def test_normalize_missing_published_date_uses_now(self):
        entry = {
            "title": "Test",
            "link": "http://example.com",
            "published": "",
            "summary": "",
        }
        article = self.scraper.normalize_article(entry)
        self.assertIsNotNone(article)
        self.assertIsNotNone(article.published)

    def test_normalize_exception_returns_none(self):
        article = self.scraper.normalize_article(None)
        self.assertIsNone(article)

    def test_normalize_source_as_dict(self):
        entry = {
            "title": "Test",
            "link": "http://example.com",
            "published": "Mon, 15 Jul 2024 12:00:00 GMT",
            "source": {"title": "Dict Source"},
        }
        article = self.scraper.normalize_article(entry)
        self.assertEqual(article.source, "Dict Source")


class TestRSSScraperFetchAll(unittest.TestCase):
    """Verify end-to-end fetch flow with mocking."""

    def test_fetch_all_deduplicates_by_url(self):
        scraper = RSSScraper()
        scraper.search_urls = ["http://example.com/rss"]

        entry_base = {
            "published": "Mon, 15 Jul 2024 12:00:00 GMT",
            "summary": "",
            "source": MagicMock(title="Src"),
        }

        with patch.object(scraper, "fetch_feed") as mock_fetch:
            mock_fetch.return_value = [
                dict(title="Article 1", link="http://ex.com/1",
                     **entry_base),
                dict(title="Article 1 Dupe", link="http://ex.com/1",
                     **entry_base),
                dict(title="Article 2", link="http://ex.com/2",
                     **entry_base),
            ]
            articles = scraper.fetch_all()

        self.assertEqual(len(articles), 2)

    def test_fetch_all_returns_empty_when_no_entries(self):
        scraper = RSSScraper()
        scraper.search_urls = ["http://ex.com/rss"]

        with patch.object(scraper, "fetch_feed") as mock_fetch:
            mock_fetch.return_value = []
            articles = scraper.fetch_all()

        self.assertEqual(len(articles), 0)

    def test_generate_search_queries_returns_google_news_urls(self):
        scraper = RSSScraper()
        urls = scraper.generate_search_queries()
        self.assertIsInstance(urls, list)
        self.assertGreater(len(urls), 0)
        for url in urls:
            self.assertIn("news.google.com", url)
