"""Fulfilment rules and their boundaries."""

from __future__ import annotations

from tests.factories import ANCHOR, make_order
from trendyol_mcp.domain import sla_breaches
from trendyol_mcp.models import OrderStatus, Severity


def test_preparation_sla_boundary_is_strict() -> None:
    """48 saat tam sınır: aşım yok sayılır, 49 saat aşım sayılır."""
    exactly = make_order(number="TY-A", created_at="2026-10-03T09:00:00+03:00")
    over = make_order(number="TY-B", created_at="2026-10-03T08:00:00+03:00")
    findings = sla_breaches([exactly, over], now=ANCHOR, sla_hours=48)
    assert [f.references for f in findings] == [("TY-B",)]


def test_long_waiting_order_escalates_to_critical() -> None:
    order = make_order(created_at="2026-10-02T01:00:00+03:00")
    findings = sla_breaches([order], now=ANCHOR, sla_hours=48)
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].code == "HAZIRLIK_GECIKTI"


def test_promised_delivery_in_the_past_is_critical() -> None:
    order = make_order(
        number="TY-C",
        status=OrderStatus.SHIPPED,
        created_at="2026-10-01T10:00:00+03:00",
        shipped_at="2026-10-02T14:00:00+03:00",
        promised_delivery_at="2026-10-04T18:00:00+03:00",
    )
    findings = sla_breaches([order], now=ANCHOR)
    assert [f.code for f in findings] == ["TESLIM_GECIKTI"]
    assert findings[0].severity is Severity.CRITICAL


def test_closed_orders_never_produce_findings() -> None:
    delivered = make_order(
        status=OrderStatus.DELIVERED,
        created_at="2026-09-20T10:00:00+03:00",
        delivered_at="2026-09-22T10:00:00+03:00",
        promised_delivery_at="2026-09-25T10:00:00+03:00",
    )
    cancelled = make_order(number="TY-D", status=OrderStatus.CANCELLED, created_at="2026-09-20T10:00:00+03:00")
    assert sla_breaches([delivered, cancelled], now=ANCHOR) == []


def test_healthy_order_is_quiet() -> None:
    assert sla_breaches([make_order(created_at="2026-10-04T13:00:00+03:00")], now=ANCHOR) == []
