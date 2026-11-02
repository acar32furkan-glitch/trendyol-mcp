"""`tools/list` yanıtını okunur biçimde yazdırır (ajanın gördüğü şemalar).

    uv run python scripts/mcp_tool_schemas.py           # parametre tablosu + özet
    uv run python scripts/mcp_tool_schemas.py --json    # tam tools/list yanıtı (JSON)

Neden ayrı betik: `trendyol-mcp tools` yalnızca ad + açıklama yazdırır; bir ajanın araç
seçerken ve argüman kurarken gördüğü asıl sözleşme `inputSchema` alanıdır. Şemayı gözle
görmek için sunucuyu gerçekten stdio üzerinden başlatmak gerekir (uydurma çıktı yok).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def server_params(source: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "trendyol_mcp", "serve", "--source", source],
    )


async def fetch(source: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Sunucuyu stdio üzerinden başlat, el sıkış, `tools/list` yanıtını ham sözlük olarak döndür."""
    async with stdio_client(server_params(source)) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        listed = await session.list_tools()
        tools = [tool.model_dump(mode="json", exclude_none=True, by_alias=True) for tool in listed.tools]
        info: dict[str, Any] = {
            "sunucu": init.server_info.name,
            "sürüm": init.server_info.version,
            "protokol": init.protocol_version,
            "talimat_bayt": len(init.instructions or ""),
            "araç": len(tools),
        }
        return info, tools


def _type_of(prop: dict[str, Any]) -> str:
    if "type" in prop:
        return str(prop["type"])
    variants = [str(part.get("type")) for part in prop.get("anyOf", []) if isinstance(part, dict)]
    return "|".join(variants) if variants else "?"


def describe(info: dict[str, Any], tools: list[dict[str, Any]]) -> str:
    compact = json.dumps(tools, ensure_ascii=False, separators=(",", ":"))
    lines = [
        f"{info['sunucu']} {info['sürüm']} · protokol {info['protokol']} · "
        f"{info['araç']} araç · tools/list {len(compact.encode())} bayt (sıkıştırılmış)",
        "",
    ]
    for tool in tools:
        schema = tool["inputSchema"]
        required = schema.get("required")
        lines.append(f"{tool['name']}")
        lines.append(
            f"  şema anahtarları : {', '.join(sorted(schema))}"
            f" · required={required if required is not None else '<yok>'}"
            f" · additionalProperties={schema.get('additionalProperties', '<yok>')}"
        )
        for name, prop in schema.get("properties", {}).items():
            lines.append(
                f"  - {name:<19} {_type_of(prop):<10} varsayılan={prop.get('default')!r}"
                f" açıklama={prop.get('description', '<yok>')}"
            )
        output = tool.get("outputSchema", {})
        lines.append(
            f"  çıktı şeması     : alanlar={sorted(output.get('properties', {})) or '<yok>'}"
            f" · additionalProperties={output.get('additionalProperties', '<yok>')}"
        )
        lines.append("")
    return "\n".join(lines)


async def run(args: argparse.Namespace) -> int:
    info, tools = await fetch(args.source)
    if args.json:
        print(json.dumps({"server": info, "tools": tools}, ensure_ascii=False, indent=2))
    else:
        print(describe(info, tools))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ajanın gördüğü MCP araç şemalarını yazdır.")
    parser.add_argument("--source", default="fixture", help="Veri kaynağı (varsayılan: fixture).")
    parser.add_argument("--json", action="store_true", help="Tam tools/list yanıtını JSON olarak ver.")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
