"""Fulfilment rules: which orders need a human today."""

from __future__ import annotations

from datetime import datetime, timedelta

from trendyol_mcp.models import Finding, Order, OrderStatus, Severity

PREPARATION_SLA_HOURS = 48
LATE_WARNING_HOURS = 72


def sla_breaches(
    orders: list[Order],
    *,
    now: datetime,
    sla_hours: int = PREPARATION_SLA_HOURS,
) -> list[Finding]:
    """Orders that break the preparation or delivery promise.

    Two independent promises are checked:

    * preparation — an order still ``CREATED``/``PICKING`` longer than ``sla_hours``;
    * delivery — a not-yet-delivered order whose ``promised_delivery_at`` already passed.
    """
    findings: list[Finding] = []
    for order in orders:
        if not order.is_open:
            continue
        waiting = now - order.created_at
        hours = waiting.total_seconds() / 3600

        late_delivery = (
            order.promised_delivery_at is not None
            and order.status is not OrderStatus.DELIVERED
            and order.promised_delivery_at < now
        )
        late_preparation = order.status in {OrderStatus.CREATED, OrderStatus.PICKING} and hours > sla_hours

        if late_delivery:
            promised = order.promised_delivery_at
            late_hours = (now - promised).total_seconds() / 3600 if promised else 0.0
            findings.append(
                Finding(
                    severity=Severity.CRITICAL,
                    code="TESLIM_GECIKTI",
                    title_tr=f"Teslim sözü geçti: {order.order_number}",
                    detail_tr=(
                        f"{order.marketplace} · {order.customer_name} · durum: {order.status.label_tr}. "
                        f"Söz verilen teslim tarihi {late_hours:.0f} saat önce geçti."
                    ),
                    action_tr="Kargo firmasıyla iletişime geçin ve müşteriye bilgi mesajı gönderin.",
                    references=(order.order_number,),
                )
            )
        elif late_preparation:
            severity = Severity.CRITICAL if hours > LATE_WARNING_HOURS else Severity.WARNING
            findings.append(
                Finding(
                    severity=severity,
                    code="HAZIRLIK_GECIKTI",
                    title_tr=f"Hazırlanmayan sipariş: {order.order_number}",
                    detail_tr=(
                        f"{order.marketplace} · {order.customer_name} · durum: {order.status.label_tr}. "
                        f"Sipariş {hours:.0f} saattir hazırlanmayı bekliyor (eşik: {sla_hours} saat)."
                    ),
                    action_tr="Siparişi bugün paketleyip kargo etiketi oluşturun.",
                    references=(order.order_number,),
                )
            )
    return findings


def promised_soon(orders: list[Order], *, now: datetime, within_hours: int = 12) -> list[Order]:
    """Open orders whose delivery promise expires within ``within_hours`` (not a finding yet)."""
    horizon = now + timedelta(hours=within_hours)
    return [
        o
        for o in orders
        if o.is_open and o.promised_delivery_at is not None and now <= o.promised_delivery_at <= horizon
    ]
