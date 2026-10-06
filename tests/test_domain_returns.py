"""Return rules: clustering, windows and rates."""

from __future__ import annotations

from decimal import Decimal

from tests.factories import ANCHOR, make_order, make_return
from trendyol_mcp.domain import return_clusters
from trendyol_mcp.domain.returns import return_rate
from trendyol_mcp.models import Severity


def test_repeating_reason_becomes_a_finding() -> None:
    returns = [
        make_return(ident="R-1", reason="Beden uyumsuz"),
        make_return(ident="R-2", reason="beden uyumsuz"),
        make_return(ident="R-3", reason="Beden uyumsuz"),
        make_return(ident="R-4", reason="Kargo hasarı"),
    ]
    findings = return_clusters(returns, now=ANCHOR, min_count=3)
    assert [f.code for f in findings] == ["IADE_KUMESI"]
    assert findings[0].severity is Severity.WARNING
    assert "3 kez" in findings[0].title_tr
    assert findings[0].references == ("TY-0001",)


def test_six_repeats_escalate_to_critical() -> None:
    returns = [make_return(ident=f"R-{i}", reason="Beden uyumsuz") for i in range(6)]
    findings = return_clusters(returns, now=ANCHOR, min_count=3)
    assert findings[0].severity is Severity.CRITICAL


def test_old_returns_leave_the_window() -> None:
    returns = [
        make_return(ident="R-1", reason="Beden uyumsuz", created_at="2026-08-01T09:00:00+03:00"),
        make_return(ident="R-2", reason="Beden uyumsuz", created_at="2026-08-02T09:00:00+03:00"),
        make_return(ident="R-3", reason="Beden uyumsuz", created_at="2026-08-03T09:00:00+03:00"),
    ]
    assert return_clusters(returns, now=ANCHOR, min_count=3, window_days=30) == []


def test_single_occurrence_is_quiet() -> None:
    assert return_clusters([make_return(reason="Kargo hasarı")], now=ANCHOR, min_count=3) == []


def test_return_rate_is_quantized_and_guards_against_zero_orders() -> None:
    returns = [make_return(ident="R-1"), make_return(ident="R-2")]
    orders = [make_order(number=f"TY-{i}") for i in range(4)]
    assert return_rate(returns, orders, now=ANCHOR) == Decimal("0.5")
    assert return_rate(returns, [], now=ANCHOR) == Decimal("0")
