"""Tool layer: the JSON contract an MCP client receives."""

from __future__ import annotations

import json

import pytest

from trendyol_mcp.tools import TOOL_DESCRIPTIONS, ToolProvider


def test_every_declared_tool_exists(provider: ToolProvider) -> None:
    for name in TOOL_DESCRIPTIONS:
        assert callable(getattr(provider, name)), name


def test_list_orders_is_newest_first_and_serializable(provider: ToolProvider) -> None:
    payload = provider.list_orders(limit=3)
    assert payload["count"] == 3
    assert [o["order_number"] for o in payload["orders"]] == ["TY-1012", "TY-1004", "TY-1005"]
    json.dumps(payload, ensure_ascii=False)  # ajanlara giden gövde JSON olabilmeli


def test_list_orders_status_filter(provider: ToolProvider) -> None:
    payload = provider.list_orders(status="shipped")
    assert {o["order_number"] for o in payload["orders"]} == {"TY-1003", "TY-1006"}
    assert payload["orders"][0]["status_tr"] == "kargoda"


def test_stock_alerts_counts_and_threshold(provider: ToolProvider) -> None:
    payload = provider.stock_alerts(threshold=5)
    assert payload["count"] == 3
    assert payload["counts"] == {"critical": 1, "warning": 2, "info": 0}
    assert payload["findings"][0]["code"] == "STOK_YOK"
    assert provider.stock_alerts(threshold=2)["count"] == 1


def test_sla_tool(provider: ToolProvider) -> None:
    payload = provider.sla_breaches(sla_hours=48)
    assert payload["count"] == 3
    assert payload["counts"]["critical"] == 2


def test_return_clusters_tool_exposes_rate(provider: ToolProvider) -> None:
    payload = provider.return_clusters(days=30)
    assert payload["count"] == 1
    assert payload["return_rate"] == pytest.approx(0.4167, abs=1e-4)


def test_review_tool(provider: ToolProvider) -> None:
    assert provider.unanswered_reviews(hours=24)["count"] == 2


def test_price_tool(provider: ToolProvider) -> None:
    payload = provider.price_overview()
    assert payload["count"] == 2
    assert payload["products"] == 8
    assert payload["discounted"] == 3
    assert payload["biggest_discount"]["barcode"] == "P-3006"


def test_daily_digest_returns_text_and_counts(provider: ToolProvider) -> None:
    payload = provider.daily_digest()
    assert payload["count"] == 12
    assert payload["counts"] == {"critical": 4, "warning": 7, "info": 1}
    assert payload["text_tr"].startswith("GÜNLÜK SATICI ÖZETİ")
    assert payload["source"] == "fixture"


def test_explicit_clock_overrides_the_fixture_anchor(provider: ToolProvider) -> None:
    """Saat ilerledikçe yeni siparişler SLA'yı aşar; sabit 'now' bunu ölçülebilir kılar."""
    from datetime import datetime

    later = ToolProvider(adapter=provider.adapter, now=datetime.fromisoformat("2026-10-06T09:00:00+03:00"))
    assert provider.sla_breaches(sla_hours=48)["count"] == 3
    assert later.sla_breaches(sla_hours=48)["count"] == 5
    assert later.sla_breaches(sla_hours=100)["count"] == 3
