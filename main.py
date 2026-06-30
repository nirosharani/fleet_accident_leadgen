import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger
from config import (
    FIRST_RUN_DAYS,
    DAILY_LOOKBACK_HOURS,
    MINIMUM_SCORE,
    RSS_TIMEOUT,
    MAX_RETRIES,
    MAX_RESULTS_PER_RUN,
    POSITIVE_KEYWORDS,
    NEGATIVE_KEYWORDS,
    EXCLUDED_COMPANIES as CONFIG_EXCLUDED,
)
from company_data import WATCHLIST, EXCLUDED_COMPANIES

logger = get_logger(__name__)


def main() -> None:
    print("=" * 54)
    print("Fleet Accident Lead Generation System")
    print("=" * 54)
    print()
    print("Initialization Successful.")
    print("Logger initialized.")
    print("Configuration loaded.")
    print("Company watchlist loaded.")
    print("Project ready.")


if __name__ == "__main__":
    main()
