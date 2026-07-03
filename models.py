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
class EvaluationResult:
    accepted: bool
    company: Optional[str]
    score: int
    confidence: str
    reason: Optional[str]



