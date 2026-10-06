"""The daily digest: every rule, one prioritized Turkish action list."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trendyol_mcp.adapters.base import MarketplaceAdapter
from trendyol_mcp.domain.inventory import DEFAULT_LOW_STOCK, price_anomalies, stock_alerts
from trendyol_mcp.domain.returns import return_clusters, return_rate
from trendyol_mcp.domain.reviews import unanswered_negative_reviews
from trendyol_mcp.domain.sla import PREPARATION_SLA_HOURS, sla_breaches
from trendyol_mcp.models import Digest, Finding, Severity

_SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Tunable limits. Defaults are documented in docs/rules.md."""

    low_stock: int = DEFAULT_LOW_STOCK
    sla_hours: int = PREPARATION_SLA_HOURS
    return_cluster_min: int = 3
    review_window_hours: int = 24


def build_digest(adapter: MarketplaceAdapter, *, now: datetime, thresholds: Thresholds | None = None) -> Digest:
    """Collect findings from every rule and sort them by severity, then by code."""
    limits = thresholds or Thresholds()
    orders = adapter.list_orders(limit=200)
    returns = adapter.list_returns(limit=200)
    products = adapter.list_products(limit=500)
    reviews = adapter.list_reviews(limit=200)
    # Bazı pazaryerleri ürün yorumu okuma uç noktası sunmaz (örn. Hepsiburada);
    # o durumda yorum kuralı sessizce değil, açık bir notla atlanır.
    supports_reviews = bool(getattr(adapter, "supports_reviews", True))

    findings: list[Finding] = []
    findings += sla_breaches(orders, now=now, sla_hours=limits.sla_hours)
    findings += stock_alerts(products, threshold=limits.low_stock)
    findings += return_clusters(returns, now=now, min_count=limits.return_cluster_min)
    if supports_reviews:
        findings += unanswered_negative_reviews(reviews, now=now, window_hours=limits.review_window_hours)
    findings += price_anomalies(products)

    rate = return_rate(returns, orders, now=now)
    if orders or returns:
        findings.append(
            Finding(
                severity=Severity.INFO,
                code="IADE_ORANI",
                title_tr=f"Son 30 günün iade oranı: %{rate * 100:.1f}",
                detail_tr=(
                    f"İncelenen {len(orders)} sipariş ve {len(returns)} iade talebi üzerinden hesaplandı"
                    f" ({adapter.name} kaynağı)."
                ),
                action_tr="Oran %10'un üzerindeyse iade nedenleri kümesine öncelik verin.",
            )
        )

    ordered = tuple(sorted(findings, key=lambda f: (_SEVERITY_ORDER[f.severity], f.code, f.title_tr)))
    notes: tuple[str, ...] = ()
    if not supports_reviews:
        notes = (
            f"{adapter.name} satıcı API'si ürün yorumlarını okumaya izin vermiyor; "
            "cevapsız olumsuz yorum kuralı bu kaynakta atlandı.",
            "Metrikler yalnızca sipariş, iade ve listeleme verisinden üretildi.",
        )
    return Digest(
        generated_at=now,
        marketplace=adapter.name,
        source=adapter.name,
        findings=ordered,
        notes=notes,
    )
