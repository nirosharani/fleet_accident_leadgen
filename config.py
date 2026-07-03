FIRST_RUN_DAYS = 7
DAILY_LOOKBACK_HOURS = 24
MINIMUM_SCORE = 60
RSS_TIMEOUT = 10
MAX_RETRIES = 3
MAX_RESULTS_PER_RUN = 20
COMPANY_QUERY_LIMIT = 10  # Max companies to query per RSS run (0 = no limit)

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

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar", "Chandigarh", "Dadra and Nagar Haveli",
    "Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh",
    "Lakshadweep", "Puducherry",
]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Ahmedabad",
    "Chennai", "Kolkata", "Surat", "Pune", "Jaipur",
    "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane",
    "Bhopal", "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara",
    "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad",
    "Meerut", "Rajkot", "Kalyan-Dombivli", "Vasai-Virar", "Varanasi",
    "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai",
    "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur",
    "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur",
    "Kota", "Guwahati", "Chandigarh", "Solapur", "Hubli",
    "Mysore", "Tiruchirappalli", "Bareilly", "Aligarh", "Tiruppur",
    "Moradabad", "Gurgaon", "Jalandhar", "Bhubaneswar", "Salem",
    "Thiruvananthapuram", "Bhiwandi", "Guntur", "Amravati", "Bikaner",
    "Noida", "Jamshedpur", "Bhavnagar", "Cuttack", "Kochi",
    "Nellore", "Bhilai", "Dehradun", "Durgapur", "Asansol",
    "Rourkela", "Kolhapur", "Ajmer", "Kozhikode", "Siliguri",
]

TRANSPORT_KEYWORDS = [
    "employee transport", "staff bus", "company vehicle",
    "fleet vehicle", "commercial vehicle", "company truck",
    "company van", "contractor transport", "factory transport",
    "industrial transport", "driver transporting employees",
    "employee shuttle", "staff transport", "company bus",
    "office cab", "employee cab", "company owned vehicle",
    "company car", "staff car", "employee vehicle",
    "workforce transport", "personnel carrier",
    "employee bus", "staff vehicle", "office transport",
    "works bus", "plant bus", "factory bus",
    "worker bus", "employee van", "staff shuttle",
    "company transport", "office vehicle",
    "fleet operator", "fleet owner",
    "truck", "lorry", "bus", "van",
]

ACCIDENT_KEYWORDS = [
    "accident", "collision", "crash", "overturned",
    "vehicle overturning", "driver fatality", "driver death",
    "serious injury", "multiple injuries",
    "vehicle fire after collision", "road mishap",
    "fatal", "killed", "injured", "mishap",
    "overturn", "collide", "crashed", "crashing",
    "major accident", "head-on collision", "pile-up",
]

POSITIVE_INVOLVEMENT = [
    "employee", "staff", "worker", "driver", "fleet",
    "company bus", "company truck", "company vehicle",
    "company van", "company car", "contractor",
    "transporting employees", "shuttle", "commute",
    "on duty", "duty", "work commute",
]

NEGATIVE_INVOLVEMENT = [
    "csr", "corporate social responsibility", "safety campaign",
    "road safety", "awareness program", "donates",
    "donation", "charity", "spokesperson", "commented",
    "commented on", "quarterly results", "profit",
    "investor", "share price", "stock market",
    "appointed", "promoted", "inaugurates", "launches",
    "fund", "funding", "philanthropy",
]

TARGET_COMPANY_SCORE = 30
TRANSPORT_CONTEXT_SCORE = 25
ACCIDENT_CONTEXT_SCORE = 25
INDIA_CONTEXT_SCORE = 10
FATALITY_SCORE = 10

FATALITY_KEYWORDS = [
    "fatality", "fatal", "killed", "kills", "death", "dead",
    "died", "multiple injuries", "serious injury",
    "critical", "life-threatening", "mass casualty",
    "died on spot", "declared dead", "death toll",
]

RSS_ENDPOINT = "https://news.google.com/rss/search"
