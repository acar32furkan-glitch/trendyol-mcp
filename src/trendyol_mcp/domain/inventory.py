"""Stock and price rules."""

from __future__ import annotations

from decimal import Decimal

from trendyol_mcp.models import Finding, Product, Severity

DEFAULT_LOW_STOCK = 5
DISCOUNT_ANOMALY_RATIO = Decimal("0.70")


def stock_alerts(products: list[Product], *, threshold: int = DEFAULT_LOW_STOCK) -> list[Finding]:
    """Listings at or below ``threshold`` units, stock-outs first."""
    alerts: list[Finding] = []
    for product in sorted(products, key=lambda p: p.stock):
        if product.stock > threshold:
            continue
        out_of_stock = product.stock == 0
        stock_text = "tükendi" if out_of_stock else f"{product.stock} adede düştü"
        alerts.append(
            Finding(
                severity=Severity.CRITICAL if out_of_stock else Severity.WARNING,
                code="STOK_YOK" if out_of_stock else "STOK_AZ",
                title_tr=("Satışa kapalı: " if out_of_stock else "Kritik stok: ") + product.title,
                detail_tr=f"{product.barcode} barkodlu üründe stok {stock_text} (eşik: {threshold}).",
                action_tr=(
                    "Stok girişini bugün yapın; ürün aramada geriye düşmeden önce miktar girin."
                    if out_of_stock
                    else "Tedarikçiye sipariş açın, 3 günlük satış hızına göre miktar belirleyin."
                ),
                references=(product.barcode,),
            )
        )
    return alerts


def price_anomalies(products: list[Product]) -> list[Finding]:
    """Listings whose discount looks like a data-entry mistake.

    Two cases are flagged: price listed *above* the list price, and a discount deeper than
    70% (typical for a missing digit or a mis-typed decimal separator).
    """
    findings: list[Finding] = []
    for product in products:
        if product.list_price is None or product.list_price <= 0:
            continue
        if product.price > product.list_price:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="FIYAT_LISTEDEN_YUKSEK",
                    title_tr=f"Fiyat listeden yüksek: {product.title}",
                    detail_tr=(
                        f"Satış fiyatı {product.price:.2f} TL, liste fiyatı {product.list_price:.2f} TL. "
                        "İndirimli görünmesi gereken ürün indirimsiz görünüyor."
                    ),
                    action_tr="Fiyat alanlarını kontrol edin; indirim oranını yeniden tanımlayın.",
                    references=(product.barcode,),
                )
            )
            continue
        ratio = (product.list_price - product.price) / product.list_price
        if ratio >= DISCOUNT_ANOMALY_RATIO:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="INDIRIM_ANORMAL",
                    title_tr=f"Olağandışı indirim (%{ratio * 100:.0f}): {product.title}",
                    detail_tr=(
                        f"Liste {product.list_price:.2f} TL → satış {product.price:.2f} TL. "
                        "Bu oran genelde eksik haneli fiyat girişinden kaynaklanır."
                    ),
                    action_tr="Fiyatı doğrulayın; hatalıysa düzeltin, doğruysa kampanya kaydını açın.",
                    references=(product.barcode,),
                )
            )
    return findings
