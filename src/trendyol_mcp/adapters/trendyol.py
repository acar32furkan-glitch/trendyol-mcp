"""Trendyol integration adapter (read-only).

Only ``GET`` requests are issued. Credentials come from the environment and are never
logged or echoed. HTTP behaviour is covered by ``respx``-mocked tests; the live endpoints
are documented at https://developers.trendyol.com (Marketplace Integration API).

Note: this project is not affiliated with Trendyol. It reads a seller's own data with the
seller's own credentials.
"""

from __future__ import annotations

import base64
from datetime import UTC, date, datetime
from typing import Any, Final

import httpx

from trendyol_mcp.adapters.base import NotConfiguredError
from trendyol_mcp.adapters.http import request_json
from trendyol_mcp.adapters.parsing import as_decimal, as_optional_str, first_value, parse_datetime
from trendyol_mcp.config import TrendyolCredentials
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
    "created": OrderStatus.CREATED,
    "picking": OrderStatus.PICKING,
    "invoiced": OrderStatus.INVOICED,
    "shipped": OrderStatus.SHIPPED,
    "atcollectionpoint": OrderStatus.SHIPPED,
    "delivered": OrderStatus.DELIVERED,
    "cancelled": OrderStatus.CANCELLED,
    "undelivered": OrderStatus.RETURNED,
    "returned": OrderStatus.RETURNED,
    "unpacked": OrderStatus.PICKING,
}

_CLAIM_STATUS: Final[dict[str, ReturnStatus]] = {
    "created": ReturnStatus.REQUESTED,
    "waitinginstoreapprove": ReturnStatus.REQUESTED,
    "accepted": ReturnStatus.APPROVED,
    "rejected": ReturnStatus.REJECTED,
    "refunded": ReturnStatus.REFUNDED,
}


class TrendyolAdapter:
    """Read-only client for the Trendyol Marketplace Integration API."""

    name = "trendyol"
    supports_reviews = True

    def __init__(
        self,
        credentials: TrendyolCredentials | None,
        *,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ) -> None:
        if credentials is None:
            raise NotConfiguredError(
                "Trendyol kimlik bilgileri yok. TRENDYOL_SUPPLIER_ID, TRENDYOL_API_KEY ve "
                "TRENDYOL_API_SECRET ortam değişkenlerini tanımlayın ya da `--source fixture` kullanın."
            )
        self._credentials = credentials
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        token = base64.b64encode(f"{credentials.api_key}:{credentials.api_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "User-Agent": "trendyol-mcp/0.1.0 (+https://github.com/acar32furkan-glitch/trendyol-mcp)",
        }
        self._client = client or httpx.Client(
            base_url=credentials.base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=False,
        )

    @property
    def reference_time(self) -> datetime:
        return datetime.now(tz=UTC)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TrendyolAdapter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ transport
    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Delege edilen tek taşıma noktası: ortak ``request_json`` politikası."""
        return request_json(
            self._client,
            path,
            params,
            max_retries=self._max_retries,
            backoff_seconds=self._backoff,
        )

    def _seller_path(self, suffix: str) -> str:
        return f"/integration/{suffix.format(seller=self._credentials.supplier_id)}"

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
            "startDate": int(datetime.combine(start, datetime.min.time(), tzinfo=UTC).timestamp() * 1000),
            "endDate": int(datetime.now(tz=UTC).timestamp() * 1000),
            "page": 0,
            "size": min(limit, 200),
            "orderByField": "CreatedDate",
            "orderByDirection": "DESC",
        }
        payload = self._get(self._seller_path("order/sellers/{seller}/orders"), params)
        raw_items = payload.get("content", [])
        now = self.reference_time
        orders = [self._to_order(item, now, fallback_time=now) for item in raw_items if isinstance(item, dict)]
        if status is not None:
            orders = [o for o in orders if o.status is status]
        return orders[:limit]

    def list_returns(self, *, since: date | None = None, limit: int = 100) -> list[ReturnRequest]:
        start = since or datetime.now(tz=UTC).date()
        params: dict[str, Any] = {
            "startDate": int(datetime.combine(start, datetime.min.time(), tzinfo=UTC).timestamp() * 1000),
            "endDate": int(datetime.now(tz=UTC).timestamp() * 1000),
            "page": 0,
            "size": min(limit, 200),
        }
        payload = self._get(self._seller_path("order/sellers/{seller}/claims"), params)
        raw_items = payload.get("items", payload.get("content", []))
        now = self.reference_time
        returns = [self._to_return(item, now) for item in raw_items if isinstance(item, dict)]
        return returns[:limit]

    def list_products(self, *, limit: int = 500) -> list[Product]:
        params: dict[str, Any] = {"page": 0, "size": min(limit, 200), "approved": "true"}
        payload = self._get(self._seller_path("product/sellers/{seller}/products"), params)
        raw_items = payload.get("content", payload.get("items", []))
        products = [self._to_product(item) for item in raw_items if isinstance(item, dict)]
        return products[:limit]

    def list_reviews(self, *, since: date | None = None, limit: int = 100) -> list[Review]:
        params: dict[str, Any] = {"page": 0, "size": min(limit, 200), "status": "all"}
        if since is not None:
            params["startDate"] = int(datetime.combine(since, datetime.min.time(), tzinfo=UTC).timestamp() * 1000)
        payload = self._get(self._seller_path("product/sellers/{seller}/reviews"), params)
        raw_items = payload.get("content", payload.get("items", []))
        now = self.reference_time
        return [self._to_review(item, now) for item in raw_items if isinstance(item, dict)][:limit]

    # ------------------------------------------------------------------ mapping
    def _to_order(self, raw: dict[str, Any], now: datetime, *, fallback_time: datetime) -> Order:
        created = parse_datetime(first_value(raw, "orderDate", "createdDate", "createdAt"), fallback=fallback_time)
        raw_lines = raw.get("lines") or []
        lines: list[OrderLine] = []
        for line in raw_lines:
            if not isinstance(line, dict):
                continue
            quantity = int(first_value(line, "quantity", "amount") or 0)
            if quantity <= 0:
                continue
            lines.append(
                OrderLine(
                    barcode=str(first_value(line, "barcode", "stockCode") or ""),
                    product_name=str(first_value(line, "productName", "merchantSku") or ""),
                    quantity=quantity,
                    unit_price=as_decimal(first_value(line, "price", "lineUnitPrice", "amount")),
                )
            )
        status_text = str(first_value(raw, "status", "orderStatus") or "").replace(" ", "").lower()
        return Order(
            id=str(first_value(raw, "id", "orderId", "orderNumber") or ""),
            order_number=str(first_value(raw, "orderNumber", "orderId") or ""),
            marketplace=self.name,
            status=_ORDER_STATUS.get(status_text, OrderStatus.CREATED),
            created_at=created,
            customer_name=str(first_value(raw, "customerFirstName", "customerName") or "—"),
            total_price=as_decimal(first_value(raw, "totalPrice", "packageTotalPrice", "grossAmount")),
            lines=tuple(lines),
            cargo_tracking_number=as_optional_str(first_value(raw, "cargoTrackingNumber", "shipmentTrackingNumber")),
        )

    def _to_return(self, raw: dict[str, Any], now: datetime) -> ReturnRequest:
        status_text = str(first_value(raw, "claimStatus", "status") or "").replace(" ", "").lower()
        return ReturnRequest(
            id=str(first_value(raw, "id", "claimId") or ""),
            order_number=str(first_value(raw, "orderNumber", "orderId") or ""),
            marketplace=self.name,
            status=_CLAIM_STATUS.get(status_text, ReturnStatus.REQUESTED),
            reason=str(first_value(raw, "claimReason", "reason", "customerClaimReason") or "belirtilmemiş"),
            created_at=parse_datetime(first_value(raw, "claimDate", "createdDate", "createdAt"), fallback=now),
            refund_amount=as_decimal(first_value(raw, "refundAmount", "totalPrice")),
            product_barcode=as_optional_str(first_value(raw, "barcode", "stockCode")),
        )

    def _to_product(self, raw: dict[str, Any]) -> Product:
        price = as_decimal(first_value(raw, "salePrice", "price"))
        list_price = first_value(raw, "listPrice", "marketPrice")
        return Product(
            barcode=str(first_value(raw, "barcode", "stockCode") or ""),
            title=str(first_value(raw, "title", "productName") or ""),
            marketplace=self.name,
            stock=int(first_value(raw, "quantity", "stock") or 0),
            price=price,
            list_price=as_decimal(list_price) if list_price is not None else None,
            updated_at=parse_datetime(first_value(raw, "lastUpdatedDate", "updatedAt"), fallback=datetime.now(tz=UTC)),
        )

    def _to_review(self, raw: dict[str, Any], now: datetime) -> Review:
        return Review(
            id=str(first_value(raw, "id", "reviewId") or ""),
            product_barcode=str(first_value(raw, "productId", "barcode", "stockCode") or ""),
            rating=int(first_value(raw, "rating", "starRating") or 1),
            comment=str(first_value(raw, "comment", "reviewText") or ""),
            created_at=parse_datetime(first_value(raw, "createdDate", "reviewDate"), fallback=now),
            answered=bool(first_value(raw, "answered", "hasAnswer") or False),
        )
