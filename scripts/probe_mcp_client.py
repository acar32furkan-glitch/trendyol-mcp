"""Elle doğrulama betiği: MCP istemcisiyle gerçek stdio turu.

`uv run python scripts/probe_mcp_client.py` — sunucunun el sıkışmasını, araç listesini ve
`daily_digest` çağrısını canlı olarak gösterir. (Testlerdeki aynı akışın okunabilir hâli.)
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


def text_of(block: object) -> str:
    assert isinstance(block, TextContent)
    return block.text


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "trendyol_mcp", "serve", "--source", "fixture"],
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        print("sunucu:", init.server_info.name, init.server_info.version)

        tools = await session.list_tools()
        print("araç sayısı:", len(tools.tools))
        for tool in tools.tools:
            hint = tool.annotations.read_only_hint if tool.annotations else None
            print(f"  - {tool.name:<20} readOnly={hint} :: {tool.description}")

        result = await session.call_tool("daily_digest", {})
        payload = json.loads(text_of(result.content[0])) if result.content else {}
        print("daily_digest -> bulgu:", payload.get("count"), "| dağılım:", payload.get("counts"))
        print(text_of(result.content[0]).splitlines()[0])


if __name__ == "__main__":
    asyncio.run(main())
