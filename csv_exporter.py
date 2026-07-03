import csv
import os
from datetime import datetime
from typing import Tuple

from database import DatabaseManager
from logger import get_logger

logger = get_logger(__name__)

_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

_EXPORT_COLUMNS = [
    "Company",
    "Sector",
    "Headline",
    "Summary",
    "Incident Date",
    "Source URL",
    "Source Type",
    "Score",
    "Confidence",
    "Outreach Hook",
    "Created At",
]


class CSVExporter:
    """Exports accepted incidents from the database to a timestamped CSV file."""

    @staticmethod
    def _build_filename() -> str:
        """Generate a timestamped filename in the format
        ``fleet_incidents_YYYYMMDD_HHMMSS.csv``.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"fleet_incidents_{ts}.csv"

    @staticmethod
    def export_incidents(db: DatabaseManager) -> Tuple[str, int]:
        """Export all incident records to a CSV file.

        Reads every row from ``incident_records`` via the provided
        ``DatabaseManager``, writes a UTF-8 CSV with headers to the
        ``output/`` directory.

        Args:
            db: An initialised and connected DatabaseManager instance.

        Returns:
            A tuple of ``(file_path, record_count)``.  If there are no
            incidents to export, the file is not created and the path is
            an empty string.
        """
        rows = db.fetch_all_incidents()

        if not rows:
            print("No incidents available for export.")
            logger.info("No incidents available for export.")
            return "", 0

        os.makedirs(_OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(_OUTPUT_DIR, CSVExporter._build_filename())

        try:
            with open(file_path, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(_EXPORT_COLUMNS)

                for row in rows:
                    writer.writerow([
                        row["company"],
                        row["sector"],
                        row["headline"],
                        row["summary"],
                        row["incident_date"],
                        row["source_url"],
                        row["source_type"],
                        row["score"],
                        row["confidence"],
                        row["outreach_hook"],
                        row["created_at"],
                    ])

            logger.info("Exported %d incidents to %s", len(rows), file_path)
            return file_path, len(rows)

        except OSError as e:
            logger.error("Failed to write CSV file %s: %s", file_path, e)
            raise
        except csv.Error as e:
            logger.error("CSV write error for %s: %s", file_path, e)
            raise
