"""End-to-end MCP test: start the real server over stdio and talk to it like a client would.

This is the test that answers "does it actually work as an MCP server?" — handshake, tool
discovery, read-only annotations and a real ``tools/call`` round trip.
"""

from __future__ import annotations

import json
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from trendyol_mcp.tools import TOOL_DESCRIPTIONS


def _text(block: object) -> str:
    assert isinstance(block, TextContent)
    return block.text


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "trendyol_mcp", "serve", "--source", "fixture"],
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.integration
@pytest.mark.anyio
async def test_server_handshake_tool_listing_and_call() -> None:
    async with stdio_client(_server_params()) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        assert init.server_info.name == "trendyol-mcp"
        assert "SALT OKUNUR" in (init.instructions or "")

        tools = await session.list_tools()
        assert {tool.name for tool in tools.tools} == set(TOOL_DESCRIPTIONS)
        for tool in tools.tools:
            assert tool.annotations is not None
            assert tool.annotations.read_only_hint is True, tool.name
            assert tool.annotations.destructive_hint is False, tool.name
            assert tool.input_schema is not None

        result = await session.call_tool("daily_digest", {})
        assert result.is_error is False
        payload = json.loads(_text(result.content[0]))
        assert payload["count"] == 12
        assert payload["counts"] == {"critical": 4, "warning": 7, "info": 1}
        assert payload["text_tr"].startswith("GÜNLÜK SATICI ÖZETİ")


@pytest.mark.integration
@pytest.mark.anyio
async def test_unknown_tool_is_rejected() -> None:
    async with stdio_client(_server_params()) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("sil_her_seyi", {})
        assert result.is_error is True
