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


def fixtures_dir() -> Path:
    """Directory holding bundled sample data (override with TRENDYOL_MCP_FIXTURES)."""
    override = os.environ.get(FIXTURES_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_FIXTURES_DIR
