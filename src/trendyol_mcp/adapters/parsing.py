"""Pazaryeri yanıtlarını normalize etmek için paylaşılan yardımcılar.

Trendyol ve Hepsiburada aynı alanı farklı adlarla ve farklı tiplerle gönderiyor
(``"129.9"`` / ``129.9`` / epoch milis / ISO metin). Bu yardımcılar o farkı tek yerde soğurur;
adaptörler yalnızca hangi alan adlarının deneneceğini söyler.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

KURUS = Decimal("0.01")


def first_value(mapping: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-null value among ``keys``."""
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def as_decimal(value: Any, default: str = "0") -> Decimal:
    """Convert a provider money value into ``Decimal`` quantized to kuruş.

    Conversion always goes through ``str`` so binary float artefacts cannot leak into
    invoices; rounding is half-up (money convention, not banker's rounding).
    """
    if isinstance(value, Decimal):
        candidate = value
    elif isinstance(value, bool):  # bool is an int subclass — refuse it explicitly
        return Decimal(default)
    elif isinstance(value, int | float | str):
        text = str(value).strip().replace(",", ".")
        try:
            candidate = Decimal(text)
        except InvalidOperation:
            return Decimal(default)
    else:
        return Decimal(default)
    return candidate.quantize(KURUS, rounding=ROUND_HALF_UP)


def parse_datetime(value: Any, *, fallback: datetime) -> datetime:
    """Parse epoch millis, epoch seconds, ISO text or a datetime (naive → UTC)."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, int | float) and not isinstance(value, bool):
        number = float(value)
        if number > 100_000_000_000:  # milis
            number /= 1000.0
        return datetime.fromtimestamp(number, tz=UTC)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return fallback


def as_optional_str(value: Any) -> str | None:
    """Return a trimmed string, or ``None`` when the value is empty."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_optional_datetime(value: Any) -> datetime | None:
    """Like :func:`parse_datetime`, but unparseable input yields ``None``.

    Used for provider promises (e.g. an estimated delivery date) where a fallback clock
    would silently invent a promise and could turn into a false SLA breach.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    marker = datetime(1970, 1, 1, tzinfo=UTC)
    parsed = parse_datetime(value, fallback=marker)
    return None if parsed == marker else parsed


def as_int(value: Any, default: int = 0) -> int:
    """Convert provider values such as ``"3"`` or ``3.0`` into int without raising."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip().replace(",", ".")))
        except ValueError:
            return default
    return default
