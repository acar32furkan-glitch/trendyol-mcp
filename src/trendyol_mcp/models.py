"""Normalized domain models shared by every marketplace adapter.

The models are deliberately marketplace-agnostic: an adapter's only job is to turn a
provider payload into these objects. Everything downstream (rules, digest, MCP tools)
works on this vocabulary only.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderStatus(StrEnum):
    """Order lifecycle as seen by a seller dashboard."""

    CREATED = "created"
    PICKING = "picking"
    INVOICED = "invoiced"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

    @property
    def label_tr(self) -> str:
        return {
            OrderStatus.CREATED: "yeni sipariş",
            OrderStatus.PICKING: "hazırlanıyor",
            OrderStatus.INVOICED: "faturalandı",
            OrderStatus.SHIPPED: "kargoda",
            OrderStatus.DELIVERED: "teslim edildi",
            OrderStatus.CANCELLED: "iptal",
            OrderStatus.RETURNED: "iade",
        }[self]


class ReturnStatus(StrEnum):
    """Return request lifecycle."""

    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"

    @property
    def label_tr(self) -> str:
        return {
            ReturnStatus.REQUESTED: "talep edildi",
            ReturnStatus.APPROVED: "onaylandı",
            ReturnStatus.REJECTED: "reddedildi",
            ReturnStatus.REFUNDED: "para iadesi yapıldı",
        }[self]


class OrderLine(BaseModel):
    """A single line of an order."""

    model_config = ConfigDict(frozen=True)

    barcode: str
    product_name: str
    quantity: int = Field(ge=0)
    unit_price: Decimal = Field(ge=0)


class Order(BaseModel):
    """Normalized order."""

    model_config = ConfigDict(frozen=True)

    id: str
    order_number: str
    marketplace: str
    status: OrderStatus
    created_at: datetime
    customer_name: str
    total_price: Decimal = Field(ge=0)
    currency: str = "TRY"
    lines: tuple[OrderLine, ...] = ()
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    promised_delivery_at: datetime | None = None
    cargo_tracking_number: str | None = None

    @field_validator("total_price")
    @classmethod
    def _quantize(cls, value: Decimal) -> Decimal:
        """Kuruşa yuvarla. Para için yarım yukarı yuvarlama (ROUND_HALF_UP) kullanılır."""
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def line_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def is_open(self) -> bool:
        return self.status in {
            OrderStatus.CREATED,
            OrderStatus.PICKING,
            OrderStatus.INVOICED,
            OrderStatus.SHIPPED,
        }


class ReturnRequest(BaseModel):
    """Normalized return / claim."""

    model_config = ConfigDict(frozen=True)

    id: str
    order_number: str
    marketplace: str
    status: ReturnStatus
    reason: str
    created_at: datetime
    refund_amount: Decimal = Field(default=Decimal("0"), ge=0)
    product_barcode: str | None = None


class Product(BaseModel):
    """Normalized product / listing snapshot."""

    model_config = ConfigDict(frozen=True)

    barcode: str
    title: str
    marketplace: str
    stock: int = Field(ge=0)
    price: Decimal = Field(ge=0)
    list_price: Decimal | None = None
    updated_at: datetime | None = None


class Review(BaseModel):
    """Normalized product review."""

    model_config = ConfigDict(frozen=True)

    id: str
    product_barcode: str
    rating: int = Field(ge=1, le=5)
    comment: str
    created_at: datetime
    answered: bool = False


class Severity(StrEnum):
    """Priority used by the daily digest."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    @property
    def label_tr(self) -> str:
        return {
            Severity.CRITICAL: "KRİTİK",
            Severity.WARNING: "UYARI",
            Severity.INFO: "BİLGİ",
        }[self]


class Finding(BaseModel):
    """One actionable line of the daily digest."""

    model_config = ConfigDict(frozen=True)

    severity: Severity
    code: str
    title_tr: str
    detail_tr: str
    action_tr: str
    references: tuple[str, ...] = ()


class Digest(BaseModel):
    """Prioritized daily action list."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    marketplace: str
    source: str
    findings: tuple[Finding, ...]
    notes: tuple[str, ...] = ()

    def count(self, severity: Severity) -> int:
        return sum(1 for f in self.findings if f.severity is severity)
