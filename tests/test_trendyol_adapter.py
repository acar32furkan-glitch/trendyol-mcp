"""Trendyol integration adapter: HTTP mapping, retries and error surfaces.

No network access is required — ``respx`` intercepts every request, so the mapping code is
covered without touching a real seller account.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import httpx
import pytest
import respx

from trendyol_mcp.adapters import AdapterError, NotConfiguredError, TrendyolAdapter
from trendyol_mcp.config import TrendyolCredentials
from trendyol_mcp.models import OrderStatus, ReturnStatus

CREDS = TrendyolCredentials(supplier_id="42", api_key="key", api_secret="secret")
BASE = "https://apigw.trendyol.com/integration"

ORDER_PAYLOAD = {
    "content": [
        {
            "orderNumber": "TY-5001",
            "orderDate": 1759645200000,
            "status": "Shipped",
            "customerFirstName": "Ayşe",
            "totalPrice": 250.5,
            "cargoTrackingNumber": "TRK-1",
            "lines": [{"barcode": "B1", "productName": "Ürün", "quantity": 2, "price": 125.25}],
        },
        {
            "orderNumber": "TY-5002",
            "orderDate": "2026-10-02T10:00:00+03:00",
            "status": "Created",
            "customerFirstName": "Mehmet",
            "totalPrice": 99.9,
            "lines": [],
        },
    ]
}


@pytest.fixture
def adapter() -> Iterator[TrendyolAdapter]:
    client = httpx.Client(base_url=CREDS.base_url, timeout=5.0)
    instance = TrendyolAdapter(CREDS, client=client, backoff_seconds=0.0)
    yield instance
    instance.close()


def test_missing_credentials_are_reported_clearly() -> None:
    with pytest.raises(NotConfiguredError, match="TRENDYOL_SUPPLIER_ID"):
        TrendyolAdapter(None)


def test_credentials_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDYOL_SUPPLIER_ID", "7")
    monkeypatch.setenv("TRENDYOL_API_KEY", "k")
    monkeypatch.setenv("TRENDYOL_API_SECRET", "s")
    credentials = TrendyolCredentials.from_env()
    assert credentials is not None
    assert credentials.supplier_id == "7"
    monkeypatch.delenv("TRENDYOL_API_KEY")
    assert TrendyolCredentials.from_env() is None


@respx.mock
def test_orders_are_mapped_and_filtered(adapter: TrendyolAdapter) -> None:
    respx.get(url__startswith=f"{BASE}/order/sellers/42/orders").mock(
        return_value=httpx.Response(200, json=ORDER_PAYLOAD)
    )
    orders = adapter.list_orders(since=date(2026, 10, 1), limit=50)
    assert [o.order_number for o in orders] == ["TY-5001", "TY-5002"]
    first = orders[0]
    assert first.status is OrderStatus.SHIPPED
    assert first.customer_name == "Ayşe"
    assert float(first.total_price) == 250.50
    assert first.line_count == 2
    assert first.created_at.year == 2025  # epoch milis doğru çevrildi
    assert first.cargo_tracking_number == "TRK-1"
    filtered = adapter.list_orders(status=OrderStatus.CREATED)
    assert [o.order_number for o in filtered] == ["TY-5002"]


@respx.mock
def test_returns_products_and_reviews_are_mapped(adapter: TrendyolAdapter) -> None:
    respx.get(url__startswith=f"{BASE}/order/sellers/42/claims").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "C1",
                        "orderNumber": "TY-5001",
                        "claimStatus": "Accepted",
                        "claimReason": "Beden uyumsuz",
                        "claimDate": "2026-10-01T10:00:00+03:00",
                        "refundAmount": 100,
                    }
                ]
            },
        )
    )
    respx.get(url__startswith=f"{BASE}/product/sellers/42/products").mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [
                    {
                        "barcode": "B1",
                        "title": "Ürün",
                        "quantity": 7,
                        "salePrice": 99.9,
                        "listPrice": 149.9,
                        "lastUpdatedDate": "2026-10-01T10:00:00+03:00",
                    }
                ]
            },
        )
    )
    respx.get(url__startswith=f"{BASE}/product/sellers/42/reviews").mock(
        return_value=httpx.Response(
            200,
            json={
                "content": [
                    {
                        "id": "V1",
                        "productId": "B1",
                        "rating": 2,
                        "comment": "Beklediğim gibi değil",
                        "createdDate": "2026-10-01T10:00:00+03:00",
                        "answered": False,
                    }
                ]
            },
        )
    )

    claims = adapter.list_returns(since=date(2026, 9, 1))
    assert claims[0].status is ReturnStatus.APPROVED
    assert claims[0].reason == "Beden uyumsuz"

    products = adapter.list_products()
    assert products[0].stock == 7
    assert float(products[0].list_price or 0) == 149.90

    reviews = adapter.list_reviews(since=date(2026, 9, 1))
    assert reviews[0].rating == 2
    assert reviews[0].answered is False


@respx.mock
def test_unauthorized_raises_a_clear_error(adapter: TrendyolAdapter) -> None:
    respx.get(url__startswith=f"{BASE}/order/sellers/42/orders").mock(return_value=httpx.Response(401, json={}))
    with pytest.raises(AdapterError, match="401"):
        adapter.list_orders()


@respx.mock
def test_transient_failure_is_retried(adapter: TrendyolAdapter) -> None:
    route = respx.get(url__startswith=f"{BASE}/order/sellers/42/orders")
    route.side_effect = [httpx.Response(503, json={}), httpx.Response(200, json={"content": []})]
    assert adapter.list_orders() == []
    assert route.call_count == 2


@respx.mock
def test_permanent_failure_gives_up(adapter: TrendyolAdapter) -> None:
    respx.get(url__startswith=f"{BASE}/order/sellers/42/orders").mock(return_value=httpx.Response(400, json={}))
    with pytest.raises(AdapterError, match="HTTP 400"):
        adapter.list_orders()


@respx.mock
def test_network_error_is_wrapped(adapter: TrendyolAdapter) -> None:
    respx.get(url__startswith=f"{BASE}/order/sellers/42/orders").mock(side_effect=httpx.ConnectError("koptu"))
    with pytest.raises(AdapterError, match="3 denemede"):
        adapter.list_orders()
