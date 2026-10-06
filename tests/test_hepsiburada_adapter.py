"""Hepsiburada adaptörü: eşleme, kimlik doğrulama ve "yorum yok" davranışı.

Canlı hesap olmadan doğrulanabilen tek yol, sağlayıcı yanıtlarını ``respx`` ile taklit
etmektir; bu yüzden testler yanıt biçimlerini Hepsiburada dokümantasyonundaki alan adlarıyla
kurar ve adaptörün savunmacı eşlemesini (alan adı varyasyonları dahil) sınar.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from trendyol_mcp.adapters import AdapterError, HepsiburadaAdapter, NotConfiguredError
from trendyol_mcp.adapters.parsing import as_decimal, as_int, parse_datetime
from trendyol_mcp.config import HepsiburadaCredentials
from trendyol_mcp.domain.digest import Thresholds, build_digest
from trendyol_mcp.models import OrderStatus, ReturnStatus
from trendyol_mcp.render import render_digest_text

OMS = "https://oms.test"
LISTING = "https://listing.test"


def credentials(
    *,
    merchant_id: str = "42",
    api_key: str = "gizli-anahtar",
    merchant_name: str = "ornek-magaza",
    orders_base_url: str = OMS,
    listing_base_url: str = LISTING,
) -> HepsiburadaCredentials:
    return HepsiburadaCredentials(
        merchant_id=merchant_id,
        api_key=api_key,
        merchant_name=merchant_name,
        orders_base_url=orders_base_url,
        listing_base_url=listing_base_url,
    )


def make_adapter() -> HepsiburadaAdapter:
    return HepsiburadaAdapter(credentials(), backoff_seconds=0.0)


# --------------------------------------------------------------------------- kimlik
def test_eksik_kimlik_bilgisi_net_hata_verir() -> None:
    with pytest.raises(NotConfiguredError, match="HEPSIBURADA_MERCHANT_ID"):
        HepsiburadaAdapter(None)


def test_ortam_degiskenlerinden_okuma() -> None:
    assert HepsiburadaCredentials.from_env({}) is None
    assert HepsiburadaCredentials.from_env({"HEPSIBURADA_MERCHANT_ID": "42"}) is None
    parsed = HepsiburadaCredentials.from_env({"HEPSIBURADA_MERCHANT_ID": "42", "HEPSIBURADA_API_KEY": "k"})
    assert parsed is not None
    assert parsed.merchant_id == "42"
    assert parsed.merchant_name == "trendyol-mcp"  # varsayılan
    assert parsed.orders_base_url == "https://oms-external.hepsiburada.com"
    custom = HepsiburadaCredentials.from_env(
        {
            "HEPSIBURADA_MERCHANT_ID": " 42 ",
            "HEPSIBURADA_API_KEY": " k ",
            "HEPSIBURADA_MERCHANT_NAME": "magaza",
            "HEPSIBURADA_ORDERS_BASE_URL": "https://oms.test/",
            "HEPSIBURADA_LISTING_BASE_URL": "https://listing.test/",
        }
    )
    assert custom is not None
    assert custom.merchant_id == "42"
    assert custom.orders_base_url == "https://oms.test"


@respx.mock
def test_temel_kimlik_ve_user_agent_basligi_gonderilir() -> None:
    route = respx.get(f"{OMS}/orders").mock(return_value=httpx.Response(200, json={"data": []}))
    with make_adapter() as adapter:
        adapter.list_orders(limit=5)
    request = route.calls.last.request
    assert request.headers["Authorization"].startswith("Basic ")
    assert "ornek-magaza" in request.headers["User-Agent"]


# --------------------------------------------------------------------------- siparişler
@respx.mock
def test_siparis_eslemesi_ve_durum_sozlugu() -> None:
    payload = {
        "data": [
            {
                "orderNumber": "HB-1",
                "orderDate": 1759654800000,  # 2025-10-05T09:00:00Z
                "status": "Delivered",
                "customerName": "Ayşe K.",
                "totalPrice": "349.9",
                "cargoTrackingNumber": "TR123",
                "estimatedDeliveryEndDate": "2025-10-04T18:00:00Z",
                "items": [
                    {"merchantSku": "BRK-1", "productName": "Deri Cüzdan", "quantity": 2, "price": 174.95},
                ],
            },
            {"orderNumber": "HB-2", "status": "Packaged", "items": []},
            {"orderNumber": "HB-3", "status": "BeklenmeyenDurum", "items": []},
        ]
    }
    respx.get(f"{OMS}/orders").mock(return_value=httpx.Response(200, json=payload))
    with make_adapter() as adapter:
        orders = adapter.list_orders(limit=10)

    assert [order.order_number for order in orders] == ["HB-1", "HB-2", "HB-3"]
    first = orders[0]
    assert first.status is OrderStatus.DELIVERED
    assert first.marketplace == "hepsiburada"
    assert first.total_price == as_decimal("349.9")
    assert first.customer_name == "Ayşe K."
    assert first.cargo_tracking_number == "TR123"
    assert first.created_at == datetime(2025, 10, 5, 9, 0, tzinfo=UTC)
    assert first.promised_delivery_at == datetime(2025, 10, 4, 18, 0, tzinfo=UTC)
    assert orders[1].promised_delivery_at is None  # söz gelmiyorsa uydurulmaz
    assert len(first.lines) == 1
    assert first.lines[0].barcode == "BRK-1"
    assert first.lines[0].quantity == 2
    assert orders[1].status is OrderStatus.PICKING
    assert orders[2].status is OrderStatus.CREATED  # bilinmeyen durum güvenli varsayılan
    assert orders[1].customer_name == "—"


@respx.mock
def test_siparis_durum_filtresi_ve_tarih_parametreleri() -> None:
    payload = {"data": [{"orderNumber": "A", "status": "Delivered"}, {"orderNumber": "B", "status": "Open"}]}
    route = respx.get(f"{OMS}/orders").mock(return_value=httpx.Response(200, json=payload))
    with make_adapter() as adapter:
        delivered = adapter.list_orders(status=OrderStatus.DELIVERED, limit=10)
    assert [order.order_number for order in delivered] == ["A"]
    params = route.calls.last.request.url.params
    assert params["beginDate"].endswith("Z") and "T" in params["beginDate"]
    assert params["size"] == "10"


@respx.mock
def test_sifir_adetli_satirlar_atlanir() -> None:
    payload = {
        "data": [
            {
                "orderNumber": "HB-9",
                "status": "Open",
                "items": [{"merchantSku": "X", "quantity": 0}, {"merchantSku": "Y", "quantity": "3"}],
            }
        ]
    }
    respx.get(f"{OMS}/orders").mock(return_value=httpx.Response(200, json=payload))
    with make_adapter() as adapter:
        orders = adapter.list_orders(limit=5)
    assert [line.barcode for line in orders[0].lines] == ["Y"]


# --------------------------------------------------------------------------- iadeler
@respx.mock
def test_iade_eslemesi() -> None:
    payload = {
        "data": [
            {
                "id": "R-1",
                "orderNumber": "HB-1",
                "status": "Accepted",
                "reason": "Beden uymadı",
                "claimDate": "2026-10-04T10:00:00Z",
                "refundAmount": 349.9,
                "merchantSku": "BRK-1",
            },
            {"id": "R-2", "orderNumber": "HB-2", "status": "Bilinmeyen", "reason": "x"},
        ]
    }
    respx.get(f"{OMS}/returns").mock(return_value=httpx.Response(200, json=payload))
    with make_adapter() as adapter:
        returns = adapter.list_returns(limit=10)
    assert returns[0].status is ReturnStatus.APPROVED
    assert returns[0].reason == "Beden uymadı"
    assert returns[0].refund_amount == as_decimal("349.9")
    assert returns[0].product_barcode == "BRK-1"
    assert returns[1].status is ReturnStatus.REQUESTED
    assert returns[1].reason == "x"


# --------------------------------------------------------------------------- ürünler
@respx.mock
def test_listeleme_eslemesi_ve_ic_ice_veri_sarmali() -> None:
    payload = {
        "data": {
            "listings": [
                {
                    "merchantSku": "BRK-1",
                    "hepsiburadaSku": "HBCV00001",
                    "productName": "Deri Cüzdan",
                    "price": "349.9",
                    "availableStock": "12",
                    "lastUpdatedDate": 1759654800000,
                },
                {"merchantSku": "BRK-2", "productName": "Kemer", "price": 199, "availableStock": 0},
            ]
        }
    }
    respx.get(f"{LISTING}/listings/merchantid/42").mock(return_value=httpx.Response(200, json=payload))
    with make_adapter() as adapter:
        products = adapter.list_products(limit=10)
    assert [product.barcode for product in products] == ["BRK-1", "BRK-2"]
    assert products[0].title == "Deri Cüzdan"
    assert products[0].stock == 12
    assert products[0].price == as_decimal("349.9")
    assert products[0].marketplace == "hepsiburada"
    assert products[0].list_price is None  # liste fiyatı gelmiyorsa uydurulmaz
    assert products[1].stock == 0


# --------------------------------------------------------------------------- yorumlar
def test_yorum_destegi_yok_ve_bunu_gizlemez() -> None:
    adapter = make_adapter()
    with adapter:
        assert adapter.list_reviews(limit=10) == []
    assert adapter.supports_reviews is False


@respx.mock
def test_ozet_yorum_kuralinin_atlandigini_not_duser() -> None:
    respx.get(f"{OMS}/orders").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "orderNumber": "HB-1",
                        "status": "Open",
                        "orderDate": 1759654800000,
                        "items": [{"merchantSku": "X", "quantity": 1, "price": 10}],
                    }
                ]
            },
        )
    )
    respx.get(f"{OMS}/returns").mock(return_value=httpx.Response(200, json={"data": []}))
    respx.get(f"{LISTING}/listings/merchantid/42").mock(
        return_value=httpx.Response(
            200, json={"data": [{"merchantSku": "X", "productName": "Ürün", "price": 10, "availableStock": 1}]}
        )
    )
    with make_adapter() as adapter:
        digest = build_digest(adapter, now=datetime(2026, 10, 6, 9, 0, tzinfo=UTC), thresholds=Thresholds())

    assert digest.marketplace == "hepsiburada"
    assert len(digest.notes) == 2
    text = render_digest_text(digest)
    assert "not: hepsiburada satıcı API'si ürün yorumlarını okumaya izin vermiyor" in text
    codes = {finding.code for finding in digest.findings}
    assert "YORUM_CEVAPSIZ" not in codes
    assert "IADE_ORANI" in codes


# --------------------------------------------------------------------------- hatalar
@respx.mock
def test_401_kimlik_hatasi_anlasilir_mesaj_verir() -> None:
    respx.get(f"{OMS}/orders").mock(return_value=httpx.Response(401, json={}))
    with make_adapter() as adapter, pytest.raises(AdapterError, match="401"):
        adapter.list_orders(limit=5)


@respx.mock
def test_gecici_hatalar_yeniden_denenir_ve_pes_edilir() -> None:
    respx.get(f"{LISTING}/listings/merchantid/42").mock(return_value=httpx.Response(503, json={}))
    with make_adapter() as adapter, pytest.raises(AdapterError, match="3 denemede"):
        adapter.list_products(limit=5)


@respx.mock
def test_gecici_hata_sonrasi_basarili_deneme() -> None:
    route = respx.get(f"{LISTING}/listings/merchantid/42")
    route.side_effect = [
        httpx.Response(503, json={}),
        httpx.Response(200, json={"data": []}),
    ]
    with make_adapter() as adapter:
        assert adapter.list_products(limit=5) == []


def test_yardimci_donusumler_saglam() -> None:
    """Ortak eşleme yardımcıları: bozuk girdi çökmez, varsayılana düşer."""
    assert as_decimal(None) == as_decimal("0")
    assert as_decimal("129.999") == as_decimal("130.00")
    assert as_decimal("abc") == as_decimal("0")
    assert as_int("3.7") == 3
    assert as_int(True) == 0
    now = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)
    assert parse_datetime("2026-10-05T09:00:00", fallback=now).hour == 9
    assert parse_datetime("bozuk", fallback=now) == now
    assert parse_datetime(1759654800, fallback=now).year == 2025  # saniye
