import csv
import os
from typing import Any, Optional

from logger import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_DEFAULT_CSV_PATH = os.path.join(_PROJECT_ROOT, "data", "companies.csv")

REQUIRED_COLUMNS = {"company_name", "sector", "employees", "country"}
MIN_EMPLOYEES = 2000


class CompanyLoader:

    def __init__(self, csv_path: str = _DEFAULT_CSV_PATH) -> None:
        self.csv_path = csv_path

    def load(self) -> list[dict[str, Any]]:
        if not os.path.isfile(self.csv_path):
            logger.error("Company CSV not found at %s", self.csv_path)
            raise FileNotFoundError(f"Company CSV not found: {self.csv_path}")

        records: list[dict[str, Any]] = []
        skipped = 0

        with open(self.csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                logger.error("Empty CSV or missing header row in %s", self.csv_path)
                raise ValueError("CSV file has no header row")

            header_set = {h.strip().lower() for h in reader.fieldnames}
            missing = REQUIRED_COLUMNS - header_set
            if missing:
                logger.error(
                    "CSV missing required columns: %s (found: %s)",
                    sorted(missing), sorted(header_set),
                )
                raise ValueError(f"CSV missing columns: {missing}")

            for row_num, row in enumerate(reader, start=2):
                try:
                    record = self._normalize_and_validate(row, row_num)
                    if record is not None:
                        records.append(record)
                    else:
                        skipped += 1
                except Exception as e:
                    logger.warning("Row %d: unexpected error: %s", row_num, e)
                    skipped += 1

        logger.info(
            "Loaded %d valid companies from CSV (%d rows skipped)",
            len(records), skipped,
        )
        return records

    @staticmethod
    def _normalize_and_validate(
        row: dict[str, str], row_num: int,
    ) -> Optional[dict[str, Any]]:
        company_name = (row.get("company_name") or "").strip()
        sector = (row.get("sector") or "").strip()
        country = (row.get("country") or "").strip()
        raw_aliases = (row.get("aliases") or "").strip()

        if not company_name:
            logger.warning("Row %d: skipped (empty company_name)", row_num)
            return None
        if not sector:
            logger.warning("Row %d: skipped (empty sector)", row_num)
            return None
        if not country:
            logger.warning("Row %d: skipped (empty country)", row_num)
            return None

        raw_employees = (row.get("employees") or "").strip()
        if not raw_employees:
            logger.warning("Row %d: skipped (empty employees)", row_num)
            return None

        try:
            employees = int(raw_employees)
        except ValueError:
            logger.warning(
                "Row %d: skipped (invalid employees '%s')",
                row_num, raw_employees,
            )
            return None

        if employees < MIN_EMPLOYEES:
            logger.warning(
                "Row %d: skipped (employees %d < minimum %d)",
                row_num, employees, MIN_EMPLOYEES,
            )
            return None

        aliases: list[str] = []
        if raw_aliases:
            aliases = [a.strip() for a in raw_aliases.split("|") if a.strip()]

        return {
            "company_name": company_name,
            "sector": sector,
            "employees": employees,
            "country": country,
            "aliases": aliases,
        }

    def get_companies_summary(self) -> dict[str, Any]:
        records = self.load()
        total = len(records)
        sector_dist: dict[str, int] = {}
        for r in records:
            sector_dist[r["sector"]] = sector_dist.get(r["sector"], 0) + 1
        return {
            "total": total,
            "sector_distribution": sector_dist,
            "file_path": self.csv_path,
        }
