import hashlib
import re
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from config import RSS_ENDPOINT

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "gclid", "fbclid"}

RSS_DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %Z",
    "%a, %d %b %Y %H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%d %b %Y %H:%M:%S",
]


def generate_sha256(text: str) -> str:
    """Generate a lowercase SHA-256 hex digest of the input text.

    Strips leading/trailing whitespace before hashing.
    Returns a 64-character hex string. Empty strings are handled gracefully.
    """
    sanitized = text.strip()
    return hashlib.sha256(sanitized.encode("utf-8")).hexdigest().lower()


def normalize_headline(headline: str) -> str:
    """Normalize an article headline to a clean lowercase string.

    - Converts to lowercase
    - Removes punctuation
    - Collapses extra whitespace
    - Trims leading/trailing whitespace
    """
    headline = headline.lower()
    headline = headline.translate(str.maketrans("", "", string.punctuation))
    headline = re.sub(r"\s+", " ", headline).strip()
    return headline


def normalize_url(url: str) -> str:
    """Remove common tracking parameters from a URL.

    Strips utm_source, utm_medium, utm_campaign, gclid, fbclid
    while preserving the original path and remaining query parameters.
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned_params = {
        k: v for k, v in query_params.items() if k.lower() not in TRACKING_PARAMS
    }
    new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""
    cleaned = parsed._replace(query=new_query)
    return urlunparse(cleaned)


def parse_article_date(date_string: str) -> Optional[datetime]:
    """Parse an RSS date string into a datetime object.

    Tries multiple common RSS/ISO date formats.
    Returns None if the string cannot be parsed.
    """
    if not date_string or not date_string.strip():
        return None

    date_string = date_string.strip()
    for fmt in RSS_DATE_FORMATS:
        try:
            return datetime.strptime(date_string, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_within_date_range(article_date: datetime, days: int) -> bool:
    """Return True if article_date falls within the last `days` days from now."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    return article_date >= cutoff


def build_google_rss_query(company: str, keyword: str) -> str:
    """Build a Google News RSS search URL for the given company and keyword.

    Uses the RSS_ENDPOINT from config and URL-encodes the query.
    """
    query = f"{company} {keyword}"
    encoded_query = urlencode({"q": query})
    return f"{RSS_ENDPOINT}?{encoded_query}"


def current_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()
