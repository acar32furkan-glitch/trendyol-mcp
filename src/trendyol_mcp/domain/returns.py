"""Return rules: cluster claims by reason instead of listing them one by one."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal

from trendyol_mcp.models import Finding, Order, ReturnRequest, Severity

CLUSTER_MIN_COUNT = 3
CLUSTER_WINDOW_DAYS = 30
RETURN_RATE_ALERT = Decimal("0.10")


def return_clusters(
    returns: list[ReturnRequest],
    *,
    now: datetime,
    min_count: int = CLUSTER_MIN_COUNT,
    window_days: int = CLUSTER_WINDOW_DAYS,
) -> list[Finding]:
    """Group recent claims by reason; report clusters that repeat."""
    horizon = now - timedelta(days=window_days)
    recent = [r for r in returns if r.created_at >= horizon]
    if not recent:
        return []

    counter: Counter[str] = Counter(r.reason.strip().lower() or "belirtilmemiş" for r in recent)
    refund_by_reason: dict[str, Decimal] = {}
    for item in recent:
        key = item.reason.strip().lower() or "belirtilmemiş"
        refund_by_reason[key] = refund_by_reason.get(key, Decimal("0")) + item.refund_amount

    findings: list[Finding] = []
    for reason, count in counter.most_common():
        if count < min_count:
            continue
        refund = refund_by_reason.get(reason, Decimal("0"))
        findings.append(
            Finding(
                severity=Severity.CRITICAL if count >= min_count * 2 else Severity.WARNING,
                code="IADE_KUMESI",
                title_tr=f"Tekrarlayan iade nedeni ({count} kez): {reason}",
                detail_tr=(
                    f"Son {window_days} günde {count} iade aynı nedeni gösteriyor; toplam iade tutarı {refund:.2f} TL."
                ),
                action_tr="Bu nedeni ürün kartı/açıklamasında ele alın; gerekiyorsa ölçü veya görsel güncelleyin.",
                references=tuple(sorted({r.order_number for r in recent if r.reason.strip().lower() == reason}))[:5],
            )
        )
    return findings


def return_rate(returns: list[ReturnRequest], orders: list[Order], *, now: datetime, window_days: int = 30) -> Decimal:
    """Return requests divided by orders in the same window (0 when there are no orders)."""
    horizon = now - timedelta(days=window_days)
    recent_returns = [r for r in returns if r.created_at >= horizon]
    recent_orders = [o for o in orders if o.created_at >= horizon]
    if not recent_orders:
        return Decimal("0")
    return (Decimal(len(recent_returns)) / Decimal(len(recent_orders))).quantize(Decimal("0.0001"))


def returns_since(returns: list[ReturnRequest], *, start: date) -> list[ReturnRequest]:
    """Helper for tool level filters."""
    return [r for r in returns if r.created_at.date() >= start]
