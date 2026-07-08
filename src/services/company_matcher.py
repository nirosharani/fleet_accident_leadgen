import re
from typing import Optional

from logger import get_logger
from src.repositories.company_repository import CompanyRepository

_CORPORATE_SUFFIXES = {
    "industries", "laboratories", "laboratory", "limited", "ltd",
    "private", "pvt", "services", "products", "healthcare",
    "technologies", "technology", "solutions", "international",
    "corporation", "corp", "group", "holdings", "pharmaceutical",
    "pharmaceuticals", "enterprises",
}

logger = get_logger(__name__)


class CompanyMatcher:

    def __init__(
        self,
        repository: CompanyRepository,
        excluded_companies: Optional[list[str]] = None,
    ) -> None:
        self._repository = repository
        self._excluded = excluded_companies or []
        self._cache: dict[str, dict] = {}
        self._loaded = False

    def load_cache(self) -> None:
        rows = self._repository.load_all_companies()
        for row in rows:
            name = row["company_name"]
            aliases_raw = (row["aliases"] or "").strip()
            aliases: list[str] = (
                [a.strip() for a in aliases_raw.split("|") if a.strip()]
                if aliases_raw else []
            )
            self._cache[name] = {
                "sector": row["sector"],
                "aliases": aliases,
                "match_names": self._build_match_names(name, aliases),
            }
        self._loaded = True
        logger.info(
            "CompanyMatcher cache populated with %d companies from database",
            len(self._cache),
        )

    @staticmethod
    def _build_match_names(name: str, aliases: list[str]) -> list[str]:
        names: set[str] = set()
        for n in [name] + aliases:
            n_lower = n.lower()
            names.add(n_lower)
            words = n_lower.split()
            if len(words) > 1 and words[-1] in _CORPORATE_SUFFIXES:
                names.add(" ".join(words[:-1]))
        return list(names)

    def match(self, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        for company_name, info in self._cache.items():
            for variant in info["match_names"]:
                if variant in text_lower:
                    logger.debug(
                        "CompanyMatcher matched '%s' via variant '%s'",
                        company_name, variant,
                    )
                    return company_name
        return None

    def is_excluded(self, text: str) -> bool:
        if not text or not self._excluded:
            return False
        text_lower = text.lower()
        for company in self._excluded:
            pattern = re.compile(r'\b' + re.escape(company.lower()) + r'\b')
            if pattern.search(text_lower):
                logger.debug("Matcher excluded company '%s'", company)
                return True
        return False

    def get_company_names(self) -> list[str]:
        return list(self._cache.keys())

    def get_sector(self, company_name: str) -> Optional[str]:
        info = self._cache.get(company_name)
        return info["sector"] if info else None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def company_count(self) -> int:
        return len(self._cache)
