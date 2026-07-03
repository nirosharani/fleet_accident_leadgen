"""Tests for filters.py.

Exercises the full FilterEngine pipeline including:
  - Target company detection
  - Excluded company detection
  - Date validation
  - India context validation
  - Transport / accident context detection
  - Relevance scoring
  - Confidence level assignment
  - Full article evaluation (accept / reject)
"""

import unittest
from datetime import datetime, timezone, timedelta

from models import Article
from filters import FilterEngine


_UNSET = object()


class TestFilterEngine(unittest.TestCase):
    """Exercise the FilterEngine rule-based pipeline."""

    def setUp(self):
        self.engine = FilterEngine()

    # -- helpers ------------------------------------------------------------

    def _make_article(self, title=_UNSET, summary=_UNSET, source=_UNSET,
                      published=_UNSET):
        if title is _UNSET:
            title = "Tata Steel bus accident in Jamshedpur kills two employees"
        if summary is _UNSET:
            summary = ("A bus carrying employees of Tata Steel "
                       "met with a serious accident on the "
                       "Jamshedpur highway.")
        if source is _UNSET:
            source = "Times of India"
        if published is _UNSET:
            published = datetime.now(timezone.utc)
        return Article(
            title=title,
            url="http://example.com",
            source=source,
            published=published,
            summary=summary,
        )

    # -- Target company detection -------------------------------------------

    def test_detect_target_company_found_in_title(self):
        article = self._make_article(
            title="Tata Steel employee bus overturns"
        )
        company = self.engine.detect_target_company(article)
        self.assertIsNotNone(company)
        self.assertIn("Tata Steel", company)

    def test_detect_target_company_found_in_summary(self):
        article = self._make_article(
            title="Accident on highway",
            summary="Workers of Tata Steel were injured.",
        )
        company = self.engine.detect_target_company(article)
        self.assertIsNotNone(company)

    def test_detect_target_company_not_found(self):
        article = self._make_article(
            title="Weather forecast for tomorrow",
            summary="Sunny with occasional clouds.",
        )
        self.assertIsNone(self.engine.detect_target_company(article))

    def test_detect_target_company_empty_text(self):
        article = self._make_article(title="", summary="")
        self.assertIsNone(self.engine.detect_target_company(article))

    def test_detect_target_company_case_insensitive(self):
        article = self._make_article(
            title="tata steel accident",
            summary="",
        )
        self.assertIsNotNone(
            self.engine.detect_target_company(article)
        )

    # -- Excluded company detection -----------------------------------------

    def test_detect_excluded_company_true(self):
        article = self._make_article(
            title="Delhivery delivery truck accident",
            summary="A Delhivery vehicle overturned on highway.",
        )
        self.assertTrue(self.engine.detect_excluded_company(article))

    def test_detect_excluded_company_false(self):
        article = self._make_article()
        self.assertFalse(self.engine.detect_excluded_company(article))

    def test_detect_excluded_company_empty_text(self):
        article = self._make_article(title="", summary="")
        self.assertFalse(self.engine.detect_excluded_company(article))

    def test_detect_excluded_company_partial_match(self):
        article = self._make_article(
            title="Delhiverying supplies to hospital",
            summary="",
        )
        self.assertFalse(self.engine.detect_excluded_company(article))

    # -- Date validation ----------------------------------------------------

    def test_validate_article_date_within_range(self):
        article = self._make_article(
            published=datetime.now(timezone.utc)
        )
        self.assertTrue(
            self.engine.validate_article_date(article, 7)
        )

    def test_validate_article_date_out_of_range(self):
        article = self._make_article(
            published=datetime.now(timezone.utc) - timedelta(days=30),
        )
        self.assertFalse(
            self.engine.validate_article_date(article, 7)
        )

    def test_validate_article_date_published_none(self):
        article = self._make_article(published=None)
        self.assertFalse(
            self.engine.validate_article_date(article, 7)
        )

    def test_validate_india_context_false_outside_india(self):
        article = self._make_article(
            title="Bus crash in London",
            summary="A double-decker crashed in central London.",
            source="BBC News",
        )
        self.assertFalse(self.engine.validate_india_context(article))

    # -- India context ------------------------------------------------------

    def test_validate_india_context_true_via_source(self):
        article = self._make_article(source="Times of India")
        self.assertTrue(self.engine.validate_india_context(article))

    def test_validate_india_context_true_via_city(self):
        article = self._make_article(
            summary="Accident in Mumbai",
        )
        self.assertTrue(self.engine.validate_india_context(article))

    def test_validate_india_context_true_via_state(self):
        article = self._make_article(
            summary="Incident in Maharashtra",
        )
        self.assertTrue(self.engine.validate_india_context(article))

    def test_validate_india_context_false(self):
        article = self._make_article(
            title="Bus crash in London",
            summary="A double-decker crashed in central London.",
            source="BBC News",
        )
        self.assertFalse(self.engine.validate_india_context(article))

    def test_validate_india_context_empty_text(self):
        article = self._make_article(title="", summary="", source="")
        self.assertFalse(self.engine.validate_india_context(article))

    # -- Transport context --------------------------------------------------

    def test_validate_transport_context_true(self):
        article = self._make_article()
        self.assertTrue(self.engine.validate_transport_context(article))

    def test_validate_transport_context_false(self):
        article = self._make_article(
            title="Company quarterly results exceeded expectations",
            summary="Revenue grew by 15% this quarter.",
        )
        self.assertFalse(self.engine.validate_transport_context(article))

    # -- Accident context ---------------------------------------------------

    def test_validate_accident_context_true(self):
        article = self._make_article()
        self.assertTrue(self.engine.validate_accident_context(article))

    def test_validate_accident_context_false(self):
        article = self._make_article(
            title="Company launches new sustainability initiative",
            summary="New green energy program announced.",
        )
        self.assertFalse(self.engine.validate_accident_context(article))

    # -- Scoring ------------------------------------------------------------

    def test_calculate_relevance_score_nonzero(self):
        article = self._make_article()
        score = self.engine.calculate_relevance_score(article)
        self.assertGreater(score, 0)

    def test_calculate_relevance_score_zero_without_signals(self):
        article = self._make_article(
            title="Random product launch",
            summary="Company announced a new widget.",
            source="",
        )
        score = self.engine.calculate_relevance_score(article)
        self.assertEqual(score, 0)

    # -- Confidence ---------------------------------------------------------

    def test_determine_confidence_high(self):
        self.assertEqual(self.engine.determine_confidence(95), "High")

    def test_determine_confidence_medium(self):
        self.assertEqual(self.engine.determine_confidence(80), "Medium")

    def test_determine_confidence_low(self):
        self.assertEqual(self.engine.determine_confidence(65), "Low")

    def test_determine_confidence_rejected(self):
        self.assertEqual(self.engine.determine_confidence(30), "Rejected")

    def test_determine_confidence_boundaries(self):
        self.assertEqual(self.engine.determine_confidence(90), "High")
        self.assertEqual(self.engine.determine_confidence(89), "Medium")
        self.assertEqual(self.engine.determine_confidence(75), "Medium")
        self.assertEqual(self.engine.determine_confidence(74), "Low")
        self.assertEqual(self.engine.determine_confidence(60), "Low")
        self.assertEqual(self.engine.determine_confidence(59), "Rejected")

    # -- Full evaluation ----------------------------------------------------

    def test_evaluate_article_accepted_for_valid_article(self):
        article = self._make_article()
        result = self.engine.evaluate_article(article, first_run=True)
        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.company)
        self.assertGreater(result.score, 0)

    def test_evaluate_article_rejected_no_company(self):
        article = self._make_article(
            title="Weather forecast",
            summary="Sunny skies tomorrow.",
        )
        result = self.engine.evaluate_article(article, first_run=True)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "No target company detected")

    def test_evaluate_article_rejected_excluded_company(self):
        article = self._make_article(
            title="Delhivery accident on highway",
            summary="Delhivery delivery van overturned.",
        )
        result = self.engine.evaluate_article(article, first_run=True)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "Excluded company detected")

    def test_evaluate_article_rejected_out_of_date_range(self):
        article = self._make_article(
            published=datetime.now(timezone.utc) - timedelta(days=30),
        )
        result = self.engine.evaluate_article(article, first_run=False)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "Date validation failed")

    def test_evaluate_article_handles_exception_gracefully(self):
        article = self._make_article()
        with unittest.mock.patch.object(
            self.engine, "run_initial_validation",
            side_effect=Exception("Unexpected error"),
        ):
            result = self.engine.evaluate_article(article)
        self.assertFalse(result.accepted)
        self.assertEqual(result.score, 0)

    # -- Company variants ---------------------------------------------------

    def test_company_variants_strips_corporate_suffix(self):
        variants = self.engine._company_variants("Tata Steel")
        self.assertIn("tata steel", variants)

    def test_company_variants_includes_full_name(self):
        variants = self.engine._company_variants(
            "Sun Pharmaceutical Industries"
        )
        self.assertIn("sun pharmaceutical industries", variants)
