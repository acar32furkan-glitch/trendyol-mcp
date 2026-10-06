"""Small typed factories so rule tests stay readable."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trendyol_mcp.models import (
    Order,
    OrderLine,
    OrderStatus,
    Product,
    ReturnRequest,
    ReturnStatus,
    Review,
)

ANCHOR_TEXT = "2026-10-05T09:00:00+03:00"
ANCHOR: datetime = datetime.fromisoformat(ANCHOR_TEXT)


def dt(text: str) -> datetime:
    return datetime.fromisoformat(text)


def make_order(
    *,
    number: str = "TY-0001",
    status: OrderStatus = OrderStatus.CREATED,
    created_at: str = ANCHOR_TEXT,
    promised_delivery_at: str | None = None,
    shipped_at: str | None = None,
    delivered_at: str | None = None,
    total: str = "100.00",
    lines: int = 1,
) -> Order:
    return Order(
        id=f"id-{number}",
        order_number=number,
        marketplace="test",
        status=status,
        created_at=dt(created_at),
        customer_name="Test Müşteri",
        total_price=Decimal(total),
        lines=tuple(
            OrderLine(barcode=f"B-{i}", product_name=f"Ürün {i}", quantity=1, unit_price=Decimal("50.00"))
            for i in range(lines)
        ),
        shipped_at=dt(shipped_at) if shipped_at else None,
        delivered_at=dt(delivered_at) if delivered_at else None,
        promised_delivery_at=dt(promised_delivery_at) if promised_delivery_at else None,
    )


def make_product(
    *,
    barcode: str = "B-1",
    title: str = "Ürün",
    stock: int = 100,
    price: str = "100.00",
    list_price: str | None = None,
) -> Product:
    return Product(
        barcode=barcode,
        title=title,
        marketplace="test",
        stock=stock,
        price=Decimal(price),
        list_price=Decimal(list_price) if list_price is not None else None,
    )


def make_return(
    *,
    ident: str = "R-1",
    order_number: str = "TY-0001",
    reason: str = "Beden uyumsuz",
    status: ReturnStatus = ReturnStatus.REQUESTED,
    created_at: str = ANCHOR_TEXT,
    refund: str = "100.00",
) -> ReturnRequest:
    return ReturnRequest(
        id=ident,
        order_number=order_number,
        marketplace="test",
        status=status,
        reason=reason,
        created_at=dt(created_at),
        refund_amount=Decimal(refund),
    )


def make_review(
    *,
    ident: str = "V-1",
    barcode: str = "B-1",
    rating: int = 1,
    comment: str = "Kötü",
    created_at: str = ANCHOR_TEXT,
    answered: bool = False,
) -> Review:
    return Review(
        id=ident,
        product_barcode=barcode,
        rating=rating,
        comment=comment,
        created_at=dt(created_at),
        answered=answered,
    )
