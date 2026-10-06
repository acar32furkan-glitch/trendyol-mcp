"""Fixture adapter — the reason this project can be evaluated without credentials.

The bundled dataset under ``examples/data`` is anonymized but deliberately *awkward*:
late shipments, a stock-out, a review spike and a duplicated return reason. Anything the
server claims to detect can therefore be reproduced with a single command:

    trendyol-mcp demo
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

from pydantic import TypeAdapter, ValidationError

from trendyol_mcp.adapters.base import AdapterError
from trendyol_mcp.models import Order, OrderStatus, Product, ReturnRequest, Review

_ORDERS: Final = TypeAdapter(list[Order])
_RETURNS: Final = TypeAdapter(list[ReturnRequest])
_PRODUCTS: Final = TypeAdapter(list[Product])
_REVIEWS: Final = TypeAdapter(list[Review])


@dataclass(frozen=True, slots=True)
class FixtureBundle:
    """Parsed sample dataset plus the timestamp it was authored around."""

    reference_time: datetime
    marketplace: str
    orders: tuple[Order, ...]
    returns: tuple[ReturnRequest, ...]
    products: tuple[Product, ...]
    reviews: tuple[Review, ...]


def load_bundle(root: Path) -> FixtureBundle:
    """Load ``*.json`` fixtures from ``root``.

    Raises:
        AdapterError: when a file is missing or does not match the domain models.
    """
    meta_path = root / "meta.json"
    if not meta_path.is_file():
        raise AdapterError(f"Fixture klasörü eksik veya geçersiz: {root} (meta.json bulunamadı)")

    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    reference_time = datetime.fromisoformat(str(meta["reference_time"]))
    marketplace = str(meta.get("marketplace", "fixture"))

    def read(name: str, adapter: TypeAdapter[Any]) -> tuple[Any, ...]:
        path = root / f"{name}.json"
        if not path.is_file():
            raise AdapterError(f"Fixture dosyası yok: {path.name}")
        try:
            return tuple(adapter.validate_python(json.loads(path.read_text(encoding="utf-8"))))
        except ValidationError as exc:  # pragma: no cover - defensive
            raise AdapterError(f"{path.name} şemaya uymuyor: {exc.error_count()} hata") from exc

    return FixtureBundle(
        reference_time=reference_time,
        marketplace=marketplace,
        orders=read("orders", _ORDERS),
        returns=read("returns", _RETURNS),
        products=read("products", _PRODUCTS),
        reviews=read("reviews", _REVIEWS),
    )


class FixtureAdapter:
    """Read-only adapter over a bundled sample dataset."""

    name = "fixture"
    supports_reviews = True

    def __init__(self, root: Path) -> None:
        self._root = root
        self._bundle: FixtureBundle | None = None

    @property
    def bundle(self) -> FixtureBundle:
        if self._bundle is None:
            self._bundle = load_bundle(self._root)
        return self._bundle

    @property
    def reference_time(self) -> datetime:
        return self.bundle.reference_time

    def list_orders(
        self,
        *,
        since: date | None = None,
        status: OrderStatus | None = None,
        limit: int = 100,
    ) -> list[Order]:
        items = [o for o in self.bundle.orders if since is None or o.created_at.date() >= since]
        if status is not None:
            items = [o for o in items if o.status is status]
        return sorted(items, key=lambda o: o.created_at, reverse=True)[:limit]

    def list_returns(self, *, since: date | None = None, limit: int = 100) -> list[ReturnRequest]:
        items = [r for r in self.bundle.returns if since is None or r.created_at.date() >= since]
        return sorted(items, key=lambda r: r.created_at, reverse=True)[:limit]

    def list_products(self, *, limit: int = 500) -> list[Product]:
        return list(self.bundle.products)[:limit]

    def list_reviews(self, *, since: date | None = None, limit: int = 100) -> list[Review]:
        items = [r for r in self.bundle.reviews if since is None or r.created_at.date() >= since]
        return sorted(items, key=lambda r: r.created_at, reverse=True)[:limit]
