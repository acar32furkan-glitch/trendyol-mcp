"""Review rules: unanswered negative feedback is lost revenue."""

from __future__ import annotations

from datetime import datetime, timedelta

from trendyol_mcp.models import Finding, Review, Severity

NEGATIVE_RATING = 2
ANSWER_WINDOW_HOURS = 24
CRITICAL_COUNT = 3


def unanswered_negative_reviews(
    reviews: list[Review],
    *,
    now: datetime,
    window_hours: int = ANSWER_WINDOW_HOURS,
) -> list[Finding]:
    """Negative reviews that have waited longer than ``window_hours`` without an answer."""
    horizon = now - timedelta(hours=window_hours)
    pending = [r for r in reviews if r.rating <= NEGATIVE_RATING and not r.answered and r.created_at <= horizon]
    if not pending:
        return []

    findings: list[Finding] = []
    for review in sorted(pending, key=lambda r: (r.rating, r.created_at)):
        critical = review.rating == 1 or len(pending) >= CRITICAL_COUNT
        findings.append(
            Finding(
                severity=Severity.CRITICAL if critical else Severity.WARNING,
                code="YORUM_CEVAPSIZ",
                title_tr=f"{review.rating} yıldızlı yorum yanıtsız ({review.product_barcode})",
                detail_tr=f"“{review.comment[:140]}” · {review.created_at:%d.%m.%Y} tarihinde geldi, hâlâ cevap yok.",
                action_tr="Aynı gün içinde çözüm odaklı cevap yazın; iade/değişim teklifini açıkça belirtin.",
                references=(review.product_barcode,),
            )
        )
    return findings
