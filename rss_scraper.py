import time
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

from config import COMPANY_QUERY_LIMIT, RSS_TIMEOUT, MAX_RETRIES
from company_data import WATCHLIST, EXCLUDED_COMPANIES
from logger import get_logger
from models import Article
from utils import build_google_rss_query, normalize_url, parse_article_date

logger = get_logger(__name__)

COMPANY_SEARCHES = [
    "accident India",
    "fleet accident",
    "employee transport",
    "vehicle crash",
]

SECTOR_SEARCHES = [
    "employee transport accident India",
    "staff bus accident India",
    "commercial vehicle crash India",
]


class RSSScraper:
    """Fetch and normalize articles from Google News RSS feeds.

    Generates search queries from the company watchlist, fetches RSS
    feeds, normalises entries into Article dataclass instances, and
    deduplicates by URL within a single run.
    """

    def __init__(self) -> None:
        self.search_urls: list[str] = []
        self.articles: list[Article] = []
        self._seen_urls: set[str] = set()

    def generate_search_queries(self) -> list[str]:
        """Build Google News RSS search URLs from the company watchlist.

        For each company: accident India, fleet accident,
        employee transport, vehicle crash.

        Also generates sector-wide searches.

        Respects ``COMPANY_QUERY_LIMIT`` from config — when set > 0 only the
        first N non-excluded companies are queried (useful during development).

        Returns the list of generated RSS URLs.
        """
        urls: list[str] = []
        queried = 0
        limit = COMPANY_QUERY_LIMIT

        for sector, companies in WATCHLIST.items():
            for company in companies:
                if limit and queried >= limit:
                    break
                if any(
                    excluded.lower() in company.lower()
                    for excluded in EXCLUDED_COMPANIES
                ):
                    continue
                for keyword in COMPANY_SEARCHES:
                    urls.append(build_google_rss_query(company, keyword))
                queried += 1
            if limit and queried >= limit:
                break

        for term in SECTOR_SEARCHES:
            urls.append(build_google_rss_query("", term))

        self.search_urls = urls
        logger.info("Generated %d search queries", len(urls))
        return urls

    @staticmethod
    def _sleep_with_backoff(attempt: int) -> None:
        """Sleep with exponential backoff if retries remain.

        Args:
            attempt: The current attempt number (1-indexed).
        """
        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)

    def fetch_feed(self, url: str) -> list:
        """Download and parse one RSS feed with retry logic.

        Uses ``requests`` for the HTTP layer to support timeouts,
        then passes the response content to ``feedparser`` for parsing.

        Args:
            url: The Google News RSS URL to fetch.

        Returns:
            A list of feedparser entry dicts (may be empty).
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=RSS_TIMEOUT)
                resp.raise_for_status()

                feed = feedparser.parse(resp.content)

                if feed.bozo and not feed.entries:
                    exc = getattr(feed, "bozo_exception", None)
                    logger.warning(
                        "Bozo feed (attempt %d/%d): %s — %s",
                        attempt, MAX_RETRIES, url, exc,
                    )
                    self._sleep_with_backoff(attempt)
                    continue

                logger.info(
                    "Fetched %d entries from %s", len(feed.entries), url
                )
                return feed.entries

            except requests.exceptions.Timeout:
                logger.error(
                    "Timeout (attempt %d/%d): %s",
                    attempt, MAX_RETRIES, url,
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    "HTTP error (attempt %d/%d): %s — %s",
                    attempt, MAX_RETRIES, url, e,
                )
            except Exception as e:
                logger.error(
                    "Unexpected error (attempt %d/%d): %s — %s",
                    attempt, MAX_RETRIES, url, e,
                )
            self._sleep_with_backoff(attempt)

        logger.error("All %d retries exhausted for %s", MAX_RETRIES, url)
        return []

    def normalize_article(self, entry) -> Optional[Article]:
        """Convert a feedparser entry into an Article dataclass.

        Args:
            entry: A feedparser entry object (dict-like).

        Returns:
            An Article instance, or None if normalisation fails.
        """
        try:
            headline = entry.get("title", "").strip()
            raw_url = entry.get("link", "")
            url = normalize_url(raw_url)

            published_str = entry.get("published", "") or ""
            published = parse_article_date(published_str)
            if published is None:
                published = datetime.now(timezone.utc)

            summary = entry.get("summary", "").strip()

            source_tag = entry.get("source")
            source = ""
            if source_tag and hasattr(source_tag, "title"):
                source = source_tag.title
            elif isinstance(source_tag, dict):
                source = source_tag.get("title", "")

            if not headline and not url:
                return None

            return Article(
                title=headline,
                url=url,
                source=source,
                published=published,
                summary=summary,
            )

        except Exception as e:
            logger.error("Failed to normalize article entry: %s", e)
            return None

    def fetch_all(self) -> list[Article]:
        """Fetch every generated RSS URL and normalise all articles.

        Duplicate URLs are removed within the current execution.

        Returns:
            A deduplicated list of Article instances.
        """
        if not self.search_urls:
            self.generate_search_queries()

        all_entries: list = []
        for url in self.search_urls:
            entries = self.fetch_feed(url)
            all_entries.extend(entries)

        articles: list[Article] = []
        for entry in all_entries:
            article = self.normalize_article(entry)
            if article is None:
                continue
            if article.url in self._seen_urls:
                continue
            self._seen_urls.add(article.url)
            articles.append(article)

        self.articles = articles
        logger.info(
            "Collected %d unique articles from %d entries",
            len(articles), len(all_entries),
        )
        return articles
