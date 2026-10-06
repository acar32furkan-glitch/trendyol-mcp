"""Hepsiburada merchant adapter (read-only).

Same contract as the Trendyol adapter: only ``GET`` requests, credentials from the
environment, nothing is ever written back. Field names are mapped defensively because
Hepsiburada returns slightly different keys across endpoints and versions.

**Doğrulama durumu:** uç nokta yolları ve parametre adları Hepsiburada'nın herkese açık
satıcı API dokümantasyonundaki biçime göre yazıldı ve yanıt eşlemesi ``respx`` ile
taklit edilen yanıtlarla test edildi. Gerçek bir satıcı hesabıyla canlı doğrulama
yapılmadı (bkz. ``docs/roadmap.md``). Canlı denemede alan adı sapması görülürse yalnızca
aşağıdaki ``_first_value`` tercih listeleri güncellenir.

Not: bu proje Hepsiburada ile bağlantılı değildir; satıcı kendi verisini kendi kimlik
bilgisiyle okur. "Hepsiburada" ilgili şirketin markasıdır.
"""

from __future__ import annotations

import base64
from datetime import UTC, date, datetime, time
from typing import Any, Final

import httpx

from trendyol_mcp.adapters.base import NotConfiguredError
from trendyol_mcp.adapters.http import USER_AGENT, request_json
from trendyol_mcp.adapters.parsing import (
    as_decimal,
    as_int,
    as_optional_str,
    first_value,
    parse_datetime,
    parse_optional_datetime,
)
from trendyol_mcp.config import HepsiburadaCredentials
from trendyol_mcp.models import (
    Order,
    OrderLine,
    OrderStatus,
    Product,
    ReturnRequest,
    ReturnStatus,
    Review,
)

_ORDER_STATUS: Final[dict[str, OrderStatus]] = {
    "open": OrderStatus.CREATED,
    "created": OrderStatus.CREATED,
    "new": OrderStatus.CREATED,
    "packaged": OrderStatus.PICKING,
    "picking": OrderStatus.PICKING,
    "preparing": OrderStatus.PICKING,
    "invoiced": OrderStatus.INVOICED,
    "shipped": OrderStatus.SHIPPED,
    "intransit": OrderStatus.SHIPPED,
    "in_transit": OrderStatus.SHIPPED,
    "ontheway": OrderStatus.SHIPPED,
    "delivered": OrderStatus.DELIVERED,
    "cancelled": OrderStatus.CANCELLED,
    "canceled": OrderStatus.CANCELLED,
    "cancellationrequested": OrderStatus.CANCELLED,
    "returned": OrderStatus.RETURNED,
    "undelivered": OrderStatus.RETURNED,
    "returning": OrderStatus.RETURNED,
}

_RETURN_STATUS: Final[dict[str, ReturnStatus]] = {
    "requested": ReturnStatus.REQUESTED,
    "open": ReturnStatus.REQUESTED,
    "new": ReturnStatus.REQUESTED,
    "inreview": ReturnStatus.REQUESTED,
    "waitingforapprove": ReturnStatus.REQUESTED,
    "accepted": ReturnStatus.APPROVED,
    "approved": ReturnStatus.APPROVED,
    "rejected": ReturnStatus.REJECTED,
    "declined": ReturnStatus.REJECTED,
    "refunded": ReturnStatus.REFUNDED,
    "completed": ReturnStatus.REFUNDED,
}


def _iso(value: date | datetime | None, *, end_of_day: bool = False) -> str | None:
    """Hepsiburada date filters are ISO 8601; send UTC with an explicit ``Z``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=UTC)
    else:
        clock = time.max if end_of_day else time.min
        moment = datetime.combine(value, clock, tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the record list regardless of the wrapper key the endpoint used."""
    raw = first_value(payload, "data", "items", "content", "listings") or []
    if isinstance(raw, dict):  # {"data": {"listings": [...]}}
        raw = first_value(raw, "listings", "items", "content", "data") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


class HepsiburadaAdapter:
    """Read-only client for the Hepsiburada merchant (OMS + listing) APIs."""

    name = "hepsiburada"
    supports_reviews = False  # satıcı API'sinde ürün yorumu okuma uç noktası yok

    def __init__(
        self,
        credentials: HepsiburadaCredentials | None,
        *,
        orders_client: httpx.Client | None = None,
        listing_client: httpx.Client | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ) -> None:
        if credentials is None:
            raise NotConfiguredError(
                "Hepsiburada kimlik bilgileri yok. HEPSIBURADA_MERCHANT_ID ve HEPSIBURADA_API_KEY "
                "ortam değişkenlerini tanımlayın ya da `--source fixture` kullanın."
            )
        self._credentials = credentials
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        token = base64.b64encode(f"{credentials.merchant_id}:{credentials.api_key}".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "User-Agent": f"{credentials.merchant_name} ({USER_AGENT})",
        }
        self._orders_client = orders_client or httpx.Client(
            base_url=credentials.orders_base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=False,
        )
        self._listing_client = listing_client or httpx.Client(
            base_url=credentials.listing_base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=False,
        )

    @property
    def reference_time(self) -> datetime:
        return datetime.now(tz=UTC)

    def close(self) -> None:
        self._orders_client.close()
        self._listing_client.close()

    def __enter__(self) -> HepsiburadaAdapter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ transport
    def _fetch(self, client: httpx.Client, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return request_json(
            client,
            path,
            params,
            max_retries=self._max_retries,
            backoff_seconds=self._backoff,
        )

    # ------------------------------------------------------------------ reads
    def list_orders(
        self,
        *,
        since: date | None = None,
        status: OrderStatus | None = None,
        limit: int = 100,
    ) -> list[Order]:
        start = since or datetime.now(tz=UTC).date()
        params: dict[str, Any] = {
            "beginDate": _iso(start),
            "endDate": _iso(datetime.now(tz=UTC)),
            "page": 0,
            "size": min(limit, 200),
        }
        payload = self._fetch(self._orders_client, "/orders", params)
        now = self.reference_time
        orders = [self._to_order(item, now) for item in _items(payload)]
        if status is not None:
            orders = [order for order in orders if order.status is status]
        return orders[:limit]

    def list_returns(self, *, since: date | None = None, limit: int = 100) -> list[ReturnRequest]:
        start = since or datetime.now(tz=UTC).date()
        params: dict[str, Any] = {
            "beginDate": _iso(start),
            "endDate": _iso(datetime.now(tz=UTC)),
            "page": 0,
            "size": min(limit, 200),
        }
        payload = self._fetch(self._orders_client, "/returns", params)
        now = self.reference_time
        return [self._to_return(item, now) for item in _items(payload)][:limit]

    def list_products(self, *, limit: int = 500) -> list[Product]:
        params: dict[str, Any] = {"page": 0, "size": min(limit, 200)}
        payload = self._fetch(
            self._listing_client,
            f"/listings/merchantid/{self._credentials.merchant_id}",
            params,
        )
        return [self._to_product(item) for item in _items(payload)][:limit]

    def list_reviews(self, *, since: date | None = None, limit: int = 100) -> list[Review]:
        """Hepsiburada'nın satıcı API'sinde ürün yorumu okuma uç noktası yoktur.

        Boş liste döndürülür ve ``supports_reviews = False`` olduğu için günlük özette
        yorum kuralının atlandığı açıkça belirtilir (sessiz boşluk bırakılmaz).
        """
        del since, limit
        return []

    # ------------------------------------------------------------------ mapping
    def _to_order(self, raw: dict[str, Any], now: datetime) -> Order:
        raw_lines = first_value(raw, "items", "lines", "orderItems") or []
        lines: list[OrderLine] = []
        if isinstance(raw_lines, list):
            for line in raw_lines:
                if not isinstance(line, dict):
                    continue
                quantity = as_int(first_value(line, "quantity", "amount", "piece"))
                if quantity <= 0:
                    continue
                lines.append(
                    OrderLine(
                        barcode=str(first_value(line, "merchantSku", "hepsiburadaSku", "barcode", "sku") or ""),
                        product_name=str(first_value(line, "productName", "name", "title") or ""),
                        quantity=quantity,
                        unit_price=as_decimal(first_value(line, "price", "linePrice", "unitPrice")),
                    )
                )
        status_text = str(first_value(raw, "status", "orderStatus") or "").replace(" ", "").lower()
        return Order(
            id=str(first_value(raw, "id", "orderId", "orderNumber") or ""),
            order_number=str(first_value(raw, "orderNumber", "orderId") or ""),
            marketplace=self.name,
            status=_ORDER_STATUS.get(status_text, OrderStatus.CREATED),
            created_at=parse_datetime(first_value(raw, "orderDate", "createdDate"), fallback=now),
            customer_name=str(first_value(raw, "customerName", "customerFirstName") or "—"),
            total_price=as_decimal(first_value(raw, "totalPrice", "grossAmount", "amount")),
            lines=tuple(lines),
            cargo_tracking_number=as_optional_str(
                first_value(raw, "cargoTrackingNumber", "trackingNumber", "shipmentTrackingNumber")
            ),
            promised_delivery_at=parse_optional_datetime(
                first_value(raw, "estimatedDeliveryEndDate", "promisedDeliveryDate", "deliveryDueDate")
            ),
        )

    def _to_return(self, raw: dict[str, Any], now: datetime) -> ReturnRequest:
        status_text = str(first_value(raw, "status", "claimStatus", "returnStatus") or "").replace(" ", "").lower()
        return ReturnRequest(
            id=str(first_value(raw, "id", "claimId", "returnId") or ""),
            order_number=str(first_value(raw, "orderNumber", "orderId") or ""),
            marketplace=self.name,
            status=_RETURN_STATUS.get(status_text, ReturnStatus.REQUESTED),
            reason=str(first_value(raw, "reason", "claimReason", "returnReason") or "belirtilmemiş"),
            created_at=parse_datetime(first_value(raw, "claimDate", "createdDate", "returnDate"), fallback=now),
            refund_amount=as_decimal(first_value(raw, "refundAmount", "totalPrice", "amount")),
            product_barcode=as_optional_str(first_value(raw, "merchantSku", "barcode", "sku")),
        )

    def _to_product(self, raw: dict[str, Any]) -> Product:
        list_price = first_value(raw, "listPrice", "marketPrice", "priceWithoutDiscount")
        return Product(
            barcode=str(first_value(raw, "merchantSku", "hepsiburadaSku", "barcode", "sku") or ""),
            title=str(first_value(raw, "productName", "title", "name") or ""),
            marketplace=self.name,
            stock=as_int(first_value(raw, "availableStock", "stock", "quantity")),
            price=as_decimal(first_value(raw, "price", "salePrice")),
            list_price=as_decimal(list_price) if list_price is not None else None,
            updated_at=parse_datetime(
                first_value(raw, "lastUpdatedDate", "updatedAt", "priceChangeDate"),
                fallback=datetime.now(tz=UTC),
            ),
        )
