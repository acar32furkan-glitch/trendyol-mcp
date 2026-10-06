"""Marketplace adapters: one file per provider, one shared vocabulary."""

from __future__ import annotations

from trendyol_mcp.adapters.base import AdapterError, MarketplaceAdapter, NotConfiguredError
from trendyol_mcp.adapters.fixture import FixtureAdapter, FixtureBundle
from trendyol_mcp.adapters.hepsiburada import HepsiburadaAdapter
from trendyol_mcp.adapters.trendyol import TrendyolAdapter

__all__ = [
    "AdapterError",
    "FixtureAdapter",
    "FixtureBundle",
    "HepsiburadaAdapter",
    "MarketplaceAdapter",
    "NotConfiguredError",
    "TrendyolAdapter",
]
