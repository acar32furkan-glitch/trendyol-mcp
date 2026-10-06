"""Stock and price rules."""

from __future__ import annotations

from tests.factories import make_product
from trendyol_mcp.domain import price_anomalies, stock_alerts
from trendyol_mcp.models import Severity


def test_stock_out_is_critical_and_first() -> None:
    findings = stock_alerts(
        [
            make_product(barcode="B-1", title="Dolu", stock=50),
            make_product(barcode="B-2", title="Az", stock=3),
            make_product(barcode="B-3", title="Yok", stock=0),
        ],
        threshold=5,
    )
    assert [f.code for f in findings] == ["STOK_YOK", "STOK_AZ"]
    assert findings[0].severity is Severity.CRITICAL
    assert findings[1].severity is Severity.WARNING


def test_stock_threshold_is_inclusive() -> None:
    assert [f.code for f in stock_alerts([make_product(stock=5)], threshold=5)] == ["STOK_AZ"]
    assert stock_alerts([make_product(stock=6)], threshold=5) == []


def test_price_above_list_price_is_flagged() -> None:
    findings = price_anomalies([make_product(price="249.90", list_price="199.90")])
    assert [f.code for f in findings] == ["FIYAT_LISTEDEN_YUKSEK"]


def test_deep_discount_is_flagged() -> None:
    findings = price_anomalies([make_product(price="39.90", list_price="189.90")])
    assert [f.code for f in findings] == ["INDIRIM_ANORMAL"]


def test_normal_discount_is_quiet() -> None:
    assert price_anomalies([make_product(price="129.90", list_price="199.90")]) == []
    assert price_anomalies([make_product(price="100.00", list_price=None)]) == []


def test_products_without_a_list_price_are_ignored() -> None:
    assert price_anomalies([make_product(price="0.01", list_price=None)]) == []
