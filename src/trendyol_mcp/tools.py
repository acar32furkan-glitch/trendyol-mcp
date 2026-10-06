"""MCP-ready tool layer.

Everything an agent can call lives here: plain methods that take JSON-friendly arguments
and return JSON-friendly dictionaries. The MCP server (``server.py``) and the CLI
(``cli.py demo``) both call through this layer, so behaviour cannot drift between the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from trendyol_mcp.adapters.base import MarketplaceAdapter
from trendyol_mcp.domain import (
    Thresholds,
    build_digest,
    price_anomalies,
    return_clusters,
    sla_breaches,
    stock_alerts,
    unanswered_negative_reviews,
)
from trendyol_mcp.domain.returns import return_rate
from trendyol_mcp.models import Digest, Finding, Order, Product, ReturnRequest, Review, Severity
from trendyol_mcp.render import render_digest_text

TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_orders": "Son siparişleri listeler (durum ve tarih filtresiyle). Salt okunur.",
    "list_returns": "İade ve talep kayıtlarını listeler. Salt okunur.",
    "stock_alerts": "Stok eşiğinin altına düşen ürünleri, tükenenler önce olacak şekilde döndürür.",
    "sla_breaches": "Hazırlık süresini aşan veya teslim sözü geçmiş siparişleri bulur.",
    "return_clusters": "Son N günde aynı nedenle tekrarlayan iadeleri gruplar (iade kök nedeni).",
    "unanswered_reviews": "Cevapsız kalmış olumsuz ürün yorumlarını bulur.",
    "price_overview": "Fiyat tutarsızlıklarını (listeden yüksek fiyat, olağandışı indirim) raporlar.",
    "daily_digest": "Tüm kuralları çalıştırır ve önceliklendirilmiş Türkçe aksiyon listesi üretir.",
}


def _finding_payload(finding: Finding) -> dict[str, Any]:
    return {
        "severity": finding.severity.value,
        "severity_tr": finding.severity.label_tr,
        "code": finding.code,
        "title_tr": finding.title_tr,
        "detail_tr": finding.detail_tr,
        "action_tr": finding.action_tr,
        "references": list(finding.references),
    }


def _order_payload(order: Order) -> dict[str, Any]:
    return {
        "order_number": order.order_number,
        "status": order.status.value,
        "status_tr": order.status.label_tr,
        "created_at": order.created_at.isoformat(),
        "customer_name": order.customer_name,
        "total_price": float(order.total_price),
        "currency": order.currency,
        "line_count": order.line_count,
        "cargo_tracking_number": order.cargo_tracking_number,
        "promised_delivery_at": order.promised_delivery_at.isoformat() if order.promised_delivery_at else None,
    }


def _return_payload(item: ReturnRequest) -> dict[str, Any]:
    return {
        "id": item.id,
        "order_number": item.order_number,
        "status": item.status.value,
        "status_tr": item.status.label_tr,
        "reason": item.reason,
        "created_at": item.created_at.isoformat(),
        "refund_amount": float(item.refund_amount),
    }


def _product_payload(product: Product) -> dict[str, Any]:
    return {
        "barcode": product.barcode,
        "title": product.title,
        "stock": product.stock,
        "price": float(product.price),
        "list_price": float(product.list_price) if product.list_price is not None else None,
    }


def _review_payload(review: Review) -> dict[str, Any]:
    return {
        "id": review.id,
        "product_barcode": review.product_barcode,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
        "answered": review.answered,
    }


def _envelope(
    adapter: MarketplaceAdapter,
    findings: list[Finding],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": adapter.name,
        "count": len(findings),
        "counts": {
            "critical": sum(1 for f in findings if f.severity is Severity.CRITICAL),
            "warning": sum(1 for f in findings if f.severity is Severity.WARNING),
            "info": sum(1 for f in findings if f.severity is Severity.INFO),
        },
        "findings": [_finding_payload(f) for f in findings],
    }
    if extra:
        payload.update(extra)
    return payload


@dataclass(frozen=True, slots=True)
class ToolProvider:
    """Bind an adapter once; every tool reads through it."""

    adapter: MarketplaceAdapter
    now: datetime | None = None
    fixtures_anchor: bool = True

    @property
    def clock(self) -> datetime:
        """Timestamp the rules should be evaluated at.

        Live sources use the current time; fixture sources use the anchor stored in
        ``examples/data/meta.json`` unless an explicit ``now`` was supplied.
        """
        if self.now is not None:
            return self.now
        if self.fixtures_anchor:
            return self.adapter.reference_time
        return datetime.now(tz=UTC)

    # ------------------------------------------------------------------ tools
    def list_orders(self, status: str | None = None, since: str | None = None, limit: int = 50) -> dict[str, Any]:
        parsed_status = None
        if status:
            from trendyol_mcp.models import OrderStatus

            parsed_status = OrderStatus(status.strip().lower())
        parsed_since = date.fromisoformat(since) if since else None
        orders = self.adapter.list_orders(since=parsed_since, status=parsed_status, limit=limit)
        return {
            "source": self.adapter.name,
            "count": len(orders),
            "orders": [_order_payload(o) for o in orders],
        }

    def list_returns(self, since: str | None = None, limit: int = 50) -> dict[str, Any]:
        parsed_since = date.fromisoformat(since) if since else None
        items = self.adapter.list_returns(since=parsed_since, limit=limit)
        return {
            "source": self.adapter.name,
            "count": len(items),
            "returns": [_return_payload(r) for r in items],
        }

    def stock_alerts(self, threshold: int = 5) -> dict[str, Any]:
        products = self.adapter.list_products(limit=500)
        return _envelope(self.adapter, stock_alerts(products, threshold=threshold), extra={"threshold": threshold})

    def sla_breaches(self, sla_hours: int = 48) -> dict[str, Any]:
        orders = self.adapter.list_orders(limit=200)
        findings = sla_breaches(orders, now=self.clock, sla_hours=sla_hours)
        return _envelope(self.adapter, findings, extra={"sla_hours": sla_hours})

    def return_clusters(self, days: int = 30, min_count: int = 3) -> dict[str, Any]:
        items = self.adapter.list_returns(limit=200)
        findings = return_clusters(items, now=self.clock, min_count=min_count, window_days=days)
        orders = self.adapter.list_orders(limit=200)
        rate = return_rate(items, orders, now=self.clock, window_days=days)
        return _envelope(self.adapter, findings, extra={"window_days": days, "return_rate": float(rate)})

    def unanswered_reviews(self, hours: int = 24) -> dict[str, Any]:
        reviews = self.adapter.list_reviews(limit=200)
        return _envelope(self.adapter, unanswered_negative_reviews(reviews, now=self.clock, window_hours=hours))

    def price_overview(self) -> dict[str, Any]:
        products = self.adapter.list_products(limit=500)
        anomalies = price_anomalies(products)
        discounts = [p for p in products if p.list_price and p.list_price > p.price and p.list_price > 0]
        biggest = max(discounts, key=lambda p: (p.list_price or 0) - p.price, default=None)
        extra = {
            "products": len(products),
            "discounted": len(discounts),
            "biggest_discount": (
                {
                    "barcode": biggest.barcode,
                    "title": biggest.title,
                    "list_price": float(biggest.list_price or 0),
                    "price": float(biggest.price),
                }
                if biggest is not None
                else None
            ),
        }
        return _envelope(self.adapter, anomalies, extra=extra)

    def digest(self, low_stock: int = 5, sla_hours: int = 48, return_cluster_min: int = 3) -> Digest:
        """Run every rule and return the typed digest (used by the CLI and by tests)."""
        return build_digest(
            self.adapter,
            now=self.clock,
            thresholds=Thresholds(low_stock=low_stock, sla_hours=sla_hours, return_cluster_min=return_cluster_min),
        )

    def daily_digest(self, low_stock: int = 5, sla_hours: int = 48, return_cluster_min: int = 3) -> dict[str, Any]:
        digest = self.digest(low_stock=low_stock, sla_hours=sla_hours, return_cluster_min=return_cluster_min)
        payload = _envelope(self.adapter, list(digest.findings))
        payload["generated_at"] = digest.generated_at.isoformat()
        payload["text_tr"] = render_digest_text(digest)
        return payload
