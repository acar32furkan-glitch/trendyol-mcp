"""MCP server wiring.

Thin on purpose: the tool logic already lives in :mod:`trendyol_mcp.tools`. This module only
declares the server, registers the tools with *read-only* annotations, and starts stdio.
"""

from __future__ import annotations

from collections.abc import Callable

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from trendyol_mcp import __version__
from trendyol_mcp.tools import TOOL_DESCRIPTIONS, ToolProvider

SERVER_NAME = "trendyol-mcp"
SERVER_TITLE = "Türk Pazaryeri Nöbetçisi"

INSTRUCTIONS = """\
Bu sunucu bir Türk pazaryeri satıcısının kendi verisini SALT OKUNUR biçimde okur.
Hiçbir araç sipariş, ürün, fiyat veya stok değiştirmez; yalnızca okur, kural çalıştırır ve
öneri üretir.

Kullanım önerisi:
- Günlük işe başlarken `daily_digest` çağırın: önceliklendirilmiş Türkçe aksiyon listesi döner.
- Daha dar bir soru için ilgili aracı kullanın (ör. yalnızca stok için `stock_alerts`).
- Bulgular `severity` alanıyla gelir: critical > warning > info.
- Kaynak `fixture` ise sonuçlar örnek veriyle üretilmiştir; canlı veri için sunucuyu
  TRENDYOL_SUPPLIER_ID / TRENDYOL_API_KEY / TRENDYOL_API_SECRET ile çalıştırın.
"""

_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)


def build_server(provider: ToolProvider) -> MCPServer:
    """Create the MCP server with every read-only tool bound to ``provider``."""
    server = MCPServer(
        name=SERVER_NAME,
        title=SERVER_TITLE,
        version=__version__,
        instructions=INSTRUCTIONS,
    )
    # Tek kayıt tablosu: araç listesi nerede büyürse büyüsün burada tek satır eklenir.
    registration: tuple[tuple[Callable[..., object], str], ...] = (
        (provider.list_orders, "list_orders"),
        (provider.list_returns, "list_returns"),
        (provider.stock_alerts, "stock_alerts"),
        (provider.sla_breaches, "sla_breaches"),
        (provider.return_clusters, "return_clusters"),
        (provider.unanswered_reviews, "unanswered_reviews"),
        (provider.price_overview, "price_overview"),
        (provider.daily_digest, "daily_digest"),
    )
    for function, name in registration:
        server.add_tool(function, name=name, description=TOOL_DESCRIPTIONS[name], annotations=_READ_ONLY)
    return server


def run_stdio(provider: ToolProvider) -> None:
    """Serve MCP over stdio (the transport Claude Code, Cursor and Codex expect)."""
    build_server(provider).run("stdio")
