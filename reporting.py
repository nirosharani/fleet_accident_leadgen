"""
Execution statistics tracking and processing summary reporting.

Tracks pipeline metrics during execution and generates a formatted
report for both console display and persistent logging.
"""

import os
from datetime import datetime
from typing import Optional

from logger import get_logger

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_SUMMARY_LOG = os.path.join(_LOG_DIR, "run_summary.log")

logger = get_logger(__name__)


class ProcessingStats:
    """Track execution statistics and generate a processing summary report.

    Records all key metrics during pipeline execution and produces
    a formatted report for both console display and persistent logging.

    Usage:
        stats = ProcessingStats()
        stats.start()
        # ... pipeline logic updates counters ...
        stats.generate()        # displays + saves report automatically
    """

    def __init__(self) -> None:
        self.queries_generated: int = 0
        self.feeds_fetched: int = 0
        self.articles_collected: int = 0
        self.unique_articles: int = 0
        self.accepted: int = 0
        self.rejected: int = 0
        self.duplicates_skipped: int = 0
        self.incident_records_saved: int = 0
        self.rejected_records_saved: int = 0
        self.csv_records_exported: int = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    # ---- Metric setters ----

    def set_queries_generated(self, count: int) -> None:
        """Set the total number of RSS search queries generated."""
        self.queries_generated = count

    def set_feeds_fetched(self, count: int) -> None:
        """Set the total number of RSS feeds fetched."""
        self.feeds_fetched = count

    def set_articles_collected(self, count: int) -> None:
        """Set the total number of RSS articles collected."""
        self.articles_collected = count

    def set_unique_articles(self, count: int) -> None:
        """Set the number of unique articles after deduplication."""
        self.unique_articles = count

    def article_accepted(self) -> None:
        """Increment the accepted-article counter."""
        self.accepted += 1

    def article_rejected(self) -> None:
        """Increment the rejected-article counter."""
        self.rejected += 1

    def duplicate_skipped(self) -> None:
        """Increment the duplicate-skipped counter."""
        self.duplicates_skipped += 1

    def incident_saved(self) -> None:
        """Increment the incident-records-saved counter."""
        self.incident_records_saved += 1

    def rejection_saved(self) -> None:
        """Increment the rejected-records-saved counter."""
        self.rejected_records_saved += 1

    def set_csv_records_exported(self, count: int) -> None:
        """Set the number of CSV records exported."""
        self.csv_records_exported = count

    # ---- Timing ----

    def start(self) -> None:
        """Record the pipeline start timestamp."""
        self.start_time = datetime.now()

    def stop(self) -> None:
        """Record the pipeline end timestamp."""
        self.end_time = datetime.now()

    @property
    def execution_time(self) -> str:
        """Return a human-readable execution duration (e.g. \"45s\", \"2m 30s\")."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return "N/A"

    # ---- Report generation ----

    def _generate_report(self) -> str:
        """Build the formatted report string with all metrics."""
        lines = [
            "=" * 54,
            "Fleet Accident Lead Generation Report",
            "=" * 54,
            "",
            f"RSS Queries Generated:       {self.queries_generated}",
            f"RSS Feeds Fetched:           {self.feeds_fetched}",
            f"RSS Articles Collected:      {self.articles_collected}",
            f"Unique Articles:             {self.unique_articles}",
            f"Accepted Articles:           {self.accepted}",
            f"Rejected Articles:           {self.rejected}",
            f"Duplicates Skipped:          {self.duplicates_skipped}",
            f"Incident Records Saved:      {self.incident_records_saved}",
            f"Rejected Records Saved:      {self.rejected_records_saved}",
            f"CSV Records Exported:        {self.csv_records_exported}",
            f"Execution Time:              {self.execution_time}",
            "",
            "=" * 54,
        ]
        return "\n".join(lines)

    def display_report(self) -> None:
        """Print the formatted report to the console."""
        print()
        print(self._generate_report())
        print()

    def save_report(self) -> None:
        """Append the report to ``logs/run_summary.log`` with a timestamp.

        Each run is preceded by a timestamp header and followed by a
        separator line so multiple runs are clearly delineated.
        """
        os.makedirs(_LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"--- Run: {timestamp} ---\n"
            f"{self._generate_report()}\n"
            f"{'=' * 54}\n\n"
        )
        try:
            with open(_SUMMARY_LOG, "a", encoding="utf-8") as f:
                f.write(entry)
            logger.info("Run summary appended to %s", _SUMMARY_LOG)
        except OSError as e:
            logger.error("Failed to write run summary to %s: %s", _SUMMARY_LOG, e)

    def generate(self) -> None:
        """Display the report and append it to the persistent summary log.

        Automatically calls :meth:`stop` to capture the end timestamp.
        """
        self.stop()
        self.display_report()
        self.save_report()
