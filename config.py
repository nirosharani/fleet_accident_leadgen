FIRST_RUN_DAYS = 7
DAILY_LOOKBACK_HOURS = 24
MINIMUM_SCORE = 60
RSS_TIMEOUT = 10
MAX_RETRIES = 3
MAX_RESULTS_PER_RUN = 20

POSITIVE_KEYWORDS = [
    "accident", "collision", "crash", "explosion", "fire",
    "derailment", "overturn", "spill", "cargo loss",
    "fleet accident", "truck accident", "lorry accident",
    "vehicle collision", "road accident", "highway crash",
    "container fall", "goods vehicle", "commercial vehicle",
]

NEGATIVE_KEYWORDS = [
    "sports", "entertainment", "movie", "film", "celebrity",
    "politics", "election", "cricket", "football",
    "weather forecast", "stock market", "ipo",
]

EXCLUDED_COMPANIES = [
    "delhivery", "blue dart", "dtdc", "fedex", "dhl",
    "ups", "ecom express", "xpressbees", "shadowfax",
    "uber", "ola", "rapido", "zomato", "swiggy",
    "amazon logistics", "flipkart logistics",
]

RSS_ENDPOINT = "https://news.google.com/rss/search"
