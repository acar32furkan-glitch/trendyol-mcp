"""Domain rules.

Pure functions over normalized models: no HTTP, no MCP, no environment access. Every rule
takes an explicit ``now`` so behaviour is deterministic and snapshot-testable.
"""

from __future__ import annotations

from trendyol_mcp.domain.digest import Thresholds, build_digest
from trendyol_mcp.domain.inventory import price_anomalies, stock_alerts
from trendyol_mcp.domain.returns import return_clusters
from trendyol_mcp.domain.reviews import unanswered_negative_reviews
from trendyol_mcp.domain.sla import sla_breaches

__all__ = [
    "Thresholds",
    "build_digest",
    "price_anomalies",
    "return_clusters",
    "sla_breaches",
    "stock_alerts",
    "unanswered_negative_reviews",
]
