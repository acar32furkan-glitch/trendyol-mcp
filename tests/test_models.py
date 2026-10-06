"""Model behaviour: the invariants every adapter must satisfy."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from tests.factories import make_order
from trendyol_mcp.models import OrderStatus, ReturnStatus, Severity


def test_total_price_is_quantized_to_kurus() -> None:
    order = make_order(total="100.005")
    assert order.total_price == Decimal("100.01")


def test_line_count_sums_quantities() -> None:
    order = make_order(lines=4)
    assert order.line_count == 4


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (OrderStatus.CREATED, True),
        (OrderStatus.PICKING, True),
        (OrderStatus.INVOICED, True),
        (OrderStatus.SHIPPED, True),
        (OrderStatus.DELIVERED, False),
        (OrderStatus.CANCELLED, False),
        (OrderStatus.RETURNED, False),
    ],
)
def test_is_open_covers_the_fulfilment_window(status: OrderStatus, expected: bool) -> None:
    assert make_order(status=status).is_open is expected


def test_negative_totals_are_rejected() -> None:
    with pytest.raises(ValidationError):
        make_order(total="-1")


def test_labels_are_turkish() -> None:
    assert OrderStatus.SHIPPED.label_tr == "kargoda"
    assert ReturnStatus.REFUNDED.label_tr == "para iadesi yapıldı"
    assert Severity.CRITICAL.label_tr == "KRİTİK"
