"""Runtime configuration.

Credentials are read from environment variables only — never from files committed to the
repository and never logged. When credentials are absent the CLI transparently falls back
to the bundled fixture adapter so the server stays runnable for evaluation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

FIXTURES_ENV = "TRENDYOL_MCP_FIXTURES"
DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "examples" / "data"


@dataclass(frozen=True, slots=True)
class TrendyolCredentials:
    """Trendyol seller credentials (read-only integration endpoints)."""

    supplier_id: str
    api_key: str
    api_secret: str
    base_url: str = "https://apigw.trendyol.com"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> TrendyolCredentials | None:
        source = env if env is not None else dict(os.environ)
        supplier_id = source.get("TRENDYOL_SUPPLIER_ID", "").strip()
        api_key = source.get("TRENDYOL_API_KEY", "").strip()
        api_secret = source.get("TRENDYOL_API_SECRET", "").strip()
        if not (supplier_id and api_key and api_secret):
            return None
        base_url = source.get("TRENDYOL_BASE_URL", "https://apigw.trendyol.com").rstrip("/")
        return cls(supplier_id=supplier_id, api_key=api_key, api_secret=api_secret, base_url=base_url)


@dataclass(frozen=True, slots=True)
class HepsiburadaCredentials:
    """Hepsiburada merchant credentials.

    Hepsiburada's merchant API authenticates with HTTP Basic where the username is the
    merchant id and the password is the API key, and requires a ``User-Agent`` that
    identifies the merchant. Order and listing data live on two different hosts.
    """

    merchant_id: str
    api_key: str
    merchant_name: str = "trendyol-mcp"
    orders_base_url: str = "https://oms-external.hepsiburada.com"
    listing_base_url: str = "https://listing-external.hepsiburada.com"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> HepsiburadaCredentials | None:
        source = env if env is not None else dict(os.environ)
        merchant_id = source.get("HEPSIBURADA_MERCHANT_ID", "").strip()
        api_key = source.get("HEPSIBURADA_API_KEY", "").strip()
        if not (merchant_id and api_key):
            return None
        merchant_name = source.get("HEPSIBURADA_MERCHANT_NAME", "").strip() or "trendyol-mcp"
        orders_base_url = source.get("HEPSIBURADA_ORDERS_BASE_URL", "https://oms-external.hepsiburada.com").rstrip("/")
        listing_base_url = source.get(
            "HEPSIBURADA_LISTING_BASE_URL", "https://listing-external.hepsiburada.com"
        ).rstrip("/")
        return cls(
            merchant_id=merchant_id,
            api_key=api_key,
            merchant_name=merchant_name,
            orders_base_url=orders_base_url,
            listing_base_url=listing_base_url,
        )


def fixtures_dir() -> Path:
    """Directory holding bundled sample data (override with TRENDYOL_MCP_FIXTURES)."""
    override = os.environ.get(FIXTURES_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_FIXTURES_DIR
