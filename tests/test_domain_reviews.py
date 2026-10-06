"""Review rules: only *negative* and *unanswered* and *old enough* counts."""

from __future__ import annotations

from tests.factories import ANCHOR, make_review
from trendyol_mcp.domain import unanswered_negative_reviews
from trendyol_mcp.models import Severity


def test_unanswered_negative_review_is_reported() -> None:
    review = make_review(rating=2, created_at="2026-10-03T09:00:00+03:00")
    findings = unanswered_negative_reviews([review], now=ANCHOR)
    assert [f.code for f in findings] == ["YORUM_CEVAPSIZ"]
    assert findings[0].severity is Severity.WARNING


def test_one_star_is_critical() -> None:
    review = make_review(rating=1, created_at="2026-10-02T09:00:00+03:00")
    assert unanswered_negative_reviews([review], now=ANCHOR)[0].severity is Severity.CRITICAL


def test_fresh_review_gets_a_grace_period() -> None:
    review = make_review(rating=1, created_at="2026-10-05T08:00:00+03:00")
    assert unanswered_negative_reviews([review], now=ANCHOR, window_hours=24) == []


def test_answered_and_positive_reviews_are_ignored() -> None:
    answered = make_review(ident="V-1", rating=1, created_at="2026-10-01T09:00:00+03:00", answered=True)
    positive = make_review(ident="V-2", rating=5, created_at="2026-10-01T09:00:00+03:00")
    neutral = make_review(ident="V-3", rating=3, created_at="2026-10-01T09:00:00+03:00")
    assert unanswered_negative_reviews([answered, positive, neutral], now=ANCHOR) == []
