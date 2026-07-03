import logging
import re
from typing import Optional, Tuple

from company_data import EXCLUDED_COMPANIES, WATCHLIST
from config import (
    ACCIDENT_CONTEXT_SCORE,
    ACCIDENT_KEYWORDS,
    DAILY_LOOKBACK_HOURS,
    FATALITY_KEYWORDS,
    FATALITY_SCORE,
    FIRST_RUN_DAYS,
    INDIA_CONTEXT_SCORE,
    INDIAN_CITIES,
    INDIAN_STATES,
    MINIMUM_SCORE,
    NEGATIVE_INVOLVEMENT,
    POSITIVE_INVOLVEMENT,
    TARGET_COMPANY_SCORE,
    TRANSPORT_CONTEXT_SCORE,
    TRANSPORT_KEYWORDS,
)
from models import Article, EvaluationResult
from utils import is_within_date_range

_CORPORATE_SUFFIXES = {
    "industries", "laboratories", "laboratory", "limited", "ltd",
    "private", "pvt", "services", "products", "healthcare",
    "technologies", "technology", "solutions", "international",
    "corporation", "corp", "group", "holdings", "pharmaceutical",
    "pharmaceuticals", "enterprises",
}

logger = logging.getLogger(__name__)


def _keyword_match(text: str, keywords: list[str]) -> bool:
    """Check if any keyword appears as a case-insensitive substring in text.

    Args:
        text: The text to search within.
        keywords: List of keyword strings to look for.

    Returns:
        True if at least one keyword is found, False otherwise.
    """
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False


class FilterEngine:
    """Validates articles through a series of configurable filtering steps.

    Each validation method is self-contained so it can be tested independently.
    """

    def _company_variants(self, company: str) -> list[str]:
        """Generate variant forms of a company name for flexible matching.

        Returns the full name plus a version with the last word stripped
        if it is a common corporate suffix, so that short news references
        still match.  Only one level of stripping is applied to avoid
        over-matching on very short variants.
        """
        variants = [company.lower()]
        words = company.lower().split()
        if len(words) > 1 and words[-1] in _CORPORATE_SUFFIXES:
            stripped = " ".join(words[:-1])
            if stripped not in variants:
                variants.append(stripped)
        return variants

    def detect_target_company(self, article: Article) -> Optional[str]:
        """Search article text for a watchlist company name.

        Matches the full company name (and variants with common corporate
        suffixes stripped) as a case-insensitive substring against the
        article title and summary.  Returns the first matching company name
        or None if no match is found.
        """
        if not article.title and not article.summary:
            return None
        text = f"{article.title} {article.summary}".lower()
        for sector, companies in WATCHLIST.items():
            for company in companies:
                for variant in self._company_variants(company):
                    if variant in text:
                        logger.debug("Target company detected: %s (matched via '%s')", company, variant)
                        return company
        return None

    def detect_excluded_company(self, article: Article) -> bool:
        """Check whether an excluded company name appears in article text.

        Uses whole-word matching (word boundaries) to avoid false positives
        from short company names matching inside unrelated words.
        """
        if not article.title and not article.summary:
            return False
        text = f"{article.title} {article.summary}".lower()
        for company in EXCLUDED_COMPANIES:
            pattern = re.compile(r'\b' + re.escape(company.lower()) + r'\b')
            if pattern.search(text):
                logger.debug("Excluded company detected: %s", company)
                return True
        return False

    def validate_article_date(self, article: Article, lookback_days: int = 1) -> bool:
        """Check whether the article falls within the given lookback window.

        Args:
            article: Article to validate.
            lookback_days: Maximum age in days (default 1 = daily run).
                           Pass FIRST_RUN_DAYS (7) for first-run mode.

        Returns:
            True if the article date is recent enough, False otherwise.
        """
        if article.published is None:
            return False
        return is_within_date_range(article.published, lookback_days)

    def validate_india_context(self, article: Article) -> bool:
        """Check whether the article has an India-specific context.

        Searches the title, summary and source for "India", "Indian",
        Indian state / city names, or Indian highway markers (NH/SH
        followed by digits, expressway names).
        """
        if not article.title and not article.summary and not article.source:
            return False
        text = f"{article.title} {article.summary} {article.source}".lower()

        india_keywords = ["india", "indian"]
        location_keywords = [
            loc.lower()
            for loc in list(INDIAN_STATES) + list(INDIAN_CITIES)
        ]

        for keyword in india_keywords + location_keywords:
            if keyword in text:
                logger.debug("India context matched via keyword: %s", keyword)
                return True

        if re.search(r'\bexpress\s*highway\b', text) or re.search(r'\bexpressway\b', text):
            logger.debug("India context matched via expressway / express highway reference")
            return True

        return False

    def validate_transport_context(self, article: Article) -> bool:
        """Check whether the article involves employee or fleet transport.

        Searches the article title and summary against TRANSPORT_KEYWORDS
        from config.py.  Returns True if any transport keyword matches.
        """
        text = f"{article.title} {article.summary}"
        result = _keyword_match(text, TRANSPORT_KEYWORDS)
        if result:
            logger.debug("Transport context detected in '%s'", article.title)
        return result

    def validate_accident_context(self, article: Article) -> bool:
        """Check whether the article describes a clear accident event.

        Searches the article title and summary against ACCIDENT_KEYWORDS
        from config.py.  Returns True if any accident keyword matches.
        """
        text = f"{article.title} {article.summary}"
        result = _keyword_match(text, ACCIDENT_KEYWORDS)
        if result:
            logger.debug("Accident context detected in '%s'", article.title)
        return result

    def validate_company_involvement(self, article: Article) -> bool:
        """Check whether the target company is directly involved.

        First checks NEGATIVE_INVOLVEMENT keywords that signal indirect
        mentions (CSR, commentary, financial).  If none found, checks
        POSITIVE_INVOLVEMENT keywords that confirm direct involvement.
        Falls back to True since the article has already passed transport
        and accident validation.

        Returns:
            True if the company appears to be directly involved.
        """
        text = f"{article.title} {article.summary}"

        if _keyword_match(text, NEGATIVE_INVOLVEMENT):
            logger.debug(
                "Negative involvement signal in '%s'", article.title
            )
            return False

        if _keyword_match(text, POSITIVE_INVOLVEMENT):
            logger.debug(
                "Positive involvement signal in '%s'", article.title
            )
            return True

        return True

    def calculate_relevance_score(self, article: Article) -> int:
        """Calculate a rule-based relevance score for the article.

        Accumulates points for each signal present:
            - Target company detected
            - Transport context
            - Accident context
            - India context
            - Fatality / severe injury keywords

        All scoring values are drawn from config.py.
        """
        score = 0

        if self.detect_target_company(article) is not None:
            score += TARGET_COMPANY_SCORE

        if self.validate_transport_context(article):
            score += TRANSPORT_CONTEXT_SCORE

        if self.validate_accident_context(article):
            score += ACCIDENT_CONTEXT_SCORE

        if self.validate_india_context(article):
            score += INDIA_CONTEXT_SCORE

        text = f"{article.title} {article.summary}"
        if _keyword_match(text, FATALITY_KEYWORDS):
            score += FATALITY_SCORE

        logger.debug("Relevance score for '%s': %d", article.title, score)
        return score

    @staticmethod
    def determine_confidence(score: int) -> str:
        """Map a numeric score to a confidence label.

        Rules:
            >= 90  → High
            >= 75  → Medium
            >= 60  → Low
            <  60  → Rejected
        """
        if score >= 90:
            return "High"
        if score >= 75:
            return "Medium"
        if score >= 60:
            return "Low"
        return "Rejected"

    def evaluate_article(
        self, article: Article, first_run: bool = False
    ) -> EvaluationResult:
        """Complete evaluation: validate, score, and assign confidence.

        1. Runs the 7-step validation pipeline.
        2. If validation fails → rejected with score 0.
        3. If validation passes → calculate score and confidence.
        4. Accept only if score >= MINIMUM_SCORE.

        Returns an EvaluationResult with all fields populated.
        """
        try:
            passed, company, reason = self.run_initial_validation(
                article, first_run=first_run,
            )

            if not passed:
                return EvaluationResult(
                    accepted=False,
                    company=company,
                    score=0,
                    confidence="Rejected",
                    reason=reason,
                )

            score = self.calculate_relevance_score(article)
            confidence = self.determine_confidence(score)

            if score < MINIMUM_SCORE:
                return EvaluationResult(
                    accepted=False,
                    company=company,
                    score=score,
                    confidence=confidence,
                    reason=f"Score {score} below minimum {MINIMUM_SCORE}",
                )

            return EvaluationResult(
                accepted=True,
                company=company,
                score=score,
                confidence=confidence,
                reason=None,
            )

        except Exception as e:
            logger.error(
                "Evaluation error for '%s': %s", article.title, e,
            )
            return EvaluationResult(
                accepted=False,
                company=None,
                score=0,
                confidence="Rejected",
                reason=f"Evaluation error: {e}",
            )

    def run_initial_validation(
        self, article: Article, first_run: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Run the full initial validation pipeline against one article.

        Steps performed in order:
            1. Detect a target company from the watchlist.
            2. Check for excluded companies.
            3. Validate the article date.
            4. Validate India context.
            5. Validate transport context.
            6. Validate accident context.
            7. Validate company involvement.

        Args:
            article: Article instance to validate.
            first_run: When True uses FIRST_RUN_DAYS, otherwise uses
                       DAILY_LOOKBACK_HOURS for the date check.

        Returns:
            A tuple of (passed, detected_company, rejection_reason).
            When passed is True the rejection reason is None.
        """
        try:
            lookback_days = (
                FIRST_RUN_DAYS if first_run else (DAILY_LOOKBACK_HOURS // 24)
            )

            company = self.detect_target_company(article)
            if company is None:
                logger.info(
                    "Rejected '%s': no target company detected",
                    article.title,
                )
                return False, None, "No target company detected"

            if self.detect_excluded_company(article):
                logger.info(
                    "Rejected '%s': excluded company detected",
                    article.title,
                )
                return False, company, "Excluded company detected"

            if not self.validate_article_date(article, lookback_days):
                logger.info(
                    "Rejected '%s': date validation failed",
                    article.title,
                )
                return False, company, "Date validation failed"

            if not self.validate_india_context(article):
                logger.info(
                    "Rejected '%s': no India context detected",
                    article.title,
                )
                return False, company, "No India context detected"

            if not self.validate_transport_context(article):
                logger.info(
                    "Rejected '%s': no transport context detected",
                    article.title,
                )
                return False, company, "No transport context detected"

            if not self.validate_accident_context(article):
                logger.info(
                    "Rejected '%s': no accident context detected",
                    article.title,
                )
                return False, company, "No accident context detected"

            if not self.validate_company_involvement(article):
                logger.info(
                    "Rejected '%s': company not directly involved",
                    article.title,
                )
                return False, company, "Company not directly involved"

            logger.info("Passed validation: '%s' (company=%s)", article.title, company)
            return True, company, None

        except Exception as e:
            logger.error(
                "Unexpected error validating '%s': %s", article.title, e,
            )
            return False, None, f"Validation error: {e}"
