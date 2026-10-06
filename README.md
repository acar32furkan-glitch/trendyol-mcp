# Trendyol MCP

Read-only MCP server for Turkish marketplace operations.

## What it does

- inspects orders, returns, stock, SLA, and comments
- summarizes the day in plain Turkish
- surfaces urgent issues without mutating seller state
- works with MCP clients such as Claude Code or Cursor

## Tech

- Python
- Model Context Protocol (MCP)
- CLI and service-based workflow
- Deterministic business rules

## Quick use

```bash
git clone https://github.com/acar32furkan-glitch/trendyol-mcp && cd trendyol-mcp
uv sync --all-extras --dev
uv run trendyol-mcp demo
```

## License

MIT
