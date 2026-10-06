"""Adapter contract.

Every adapter is **read-only by design**. The protocol has no create/update/delete
member, so a tool built on top of it cannot change anything on the seller's account
even by accident. See ``docs/adr/0001-read-only-by-design.md``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, runtime_checkable

from trendyol_mcp.models import Order, OrderStatus, Product, ReturnRequest, Review


class AdapterError(RuntimeError):
    """Raised when a marketplace refuses or breaks a read operation."""


class NotConfiguredError(AdapterError):
    """Raised when an adapter needs credentials that are not present."""


@runtime_checkable
class MarketplaceAdapter(Protocol):
    """Minimal read surface used by every tool."""

    name: str
    supports_reviews: bool

    @property
    def reference_time(self) -> datetime:
        """Clock the adapter's data should be interpreted with.

        Live adapters return the current time; fixture adapters return the timestamp the
        sample data was authored around, which keeps demos and snapshot tests stable.
        """
        ...

    def list_orders(
        self,
        *,
        since: date | None = None,
        status: OrderStatus | None = None,
        limit: int = 100,
    ) -> list[Order]:
        """Return orders, newest first."""
        ...

    def list_returns(self, *, since: date | None = None, limit: int = 100) -> list[ReturnRequest]:
        """Return return/claim requests, newest first."""
        ...

    def list_products(self, *, limit: int = 500) -> list[Product]:
        """Return the seller's listing snapshots."""
        ...

    def list_reviews(self, *, since: date | None = None, limit: int = 100) -> list[Review]:
        """Return product reviews, newest first."""
        ...
