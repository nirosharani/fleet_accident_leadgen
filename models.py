from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class IncidentRecord:
    article_url: str
    company_name: str
    sector: str
    title: str
    published: datetime
    score: int
    summary: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RejectedArticle:
    article_url: str
    title: str
    reason: str
    rejected_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchStatistics:
    total_articles_fetched: int = 0
    articles_rejected: int = 0
    incidents_recorded: int = 0
    companies_matched: int = 0
    run_duration_seconds: float = 0.0
    last_run: Optional[datetime] = None
