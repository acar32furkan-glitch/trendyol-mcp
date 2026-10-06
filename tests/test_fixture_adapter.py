"""Fixture adapter: loading, filtering and clear failures."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tests.factories import ANCHOR
from trendyol_mcp.adapters import AdapterError, FixtureAdapter
from trendyol_mcp.models import OrderStatus


def test_bundle_is_loaded_and_anchored(adapter: FixtureAdapter) -> None:
    bundle = adapter.bundle
    assert adapter.reference_time == ANCHOR
    assert len(bundle.orders) == 12
    assert len(bundle.returns) == 5
    assert len(bundle.products) == 8
    assert len(bundle.reviews) == 6


def test_orders_are_newest_first(adapter: FixtureAdapter) -> None:
    orders = adapter.list_orders(limit=100)
    created = [order.created_at for order in orders]
    assert created == sorted(created, reverse=True)


def test_status_and_since_filters(adapter: FixtureAdapter) -> None:
    picking = adapter.list_orders(status=OrderStatus.PICKING)
    assert {order.order_number for order in picking} == {"TY-1002", "TY-1005"}
    recent = adapter.list_orders(since=date(2026, 10, 4))
    assert all(order.created_at.date() >= date(2026, 10, 4) for order in recent)


def test_limit_is_applied(adapter: FixtureAdapter) -> None:
    assert len(adapter.list_orders(limit=3)) == 3
    assert len(adapter.list_returns(limit=2)) == 2
    assert len(adapter.list_products(limit=4)) == 4
    assert len(adapter.list_reviews(limit=1)) == 1


def test_missing_directory_raises_adapter_error(tmp_path: Path) -> None:
    with pytest.raises(AdapterError, match=r"meta\.json"):
        FixtureAdapter(tmp_path / "yok").list_orders()


def test_broken_fixture_raises_adapter_error(tmp_path: Path) -> None:
    (tmp_path / "meta.json").write_text('{"reference_time": "2026-10-05T09:00:00+03:00"}', encoding="utf-8")
    with pytest.raises(AdapterError, match="Fixture dosyası yok"):
        FixtureAdapter(tmp_path).list_orders()
