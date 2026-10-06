# trendyol-mcp

[![CI](https://github.com/acar32furkan-glitch/trendyol-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/acar32furkan-glitch/trendyol-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-2f6f9f)](https://mypy-lang.org/)

[Türkçe](README.md) · **English**

**A read-only MCP server for Turkish marketplaces.** It reads a seller's orders, returns, stock and
reviews, detects SLA breaches, stock and price traps, and turns them into **one Turkish morning
action report**. No tool ever changes anything on the seller's account.

Try it in 30 seconds — no setup, no credentials:

```bash
git clone https://github.com/acar32furkan-glitch/trendyol-mcp && cd trendyol-mcp
uv sync --all-extras --dev
uv run trendyol-mcp demo
```

![trendyol-mcp demo output](docs/assets/demo.svg)

> The report itself is Turkish by design: the people reading it at 09:00 are Turkish sellers. Code,
> docstrings and the interface are English.

---

## Why

A seller's morning is spent switching between dashboards: "any orders still unpacked, what went out
of stock, which review is unanswered, why do returns keep repeating". That work happens across four
or five screens, by hand, in no particular order. trendyol-mcp collects those questions in one place
and returns a **severity-ordered action list** — over MCP to Claude Code / Cursor / Codex, or straight
to the terminal.

The most important design decision: the tool only **reads**. A model cannot accidentally update a
price or cancel an order, because no such method exists in the adapter protocol
([ADR-0001](docs/adr/0001-read-only-by-design.md)).

## Connecting an MCP client

```json
{
  "mcpServers": {
    "trendyol-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/full/path/to/trendyol-mcp", "trendyol-mcp", "serve", "--source", "auto"]
    }
  }
}
```

`--source auto` uses live credentials when present and falls back to the bundled sample dataset
otherwise. Every tool is advertised with `readOnlyHint: true`, and the server's `instructions` field
tells the agent that nothing can be modified.

## Tools

| Tool | What it does | Returns |
|------|--------------|---------|
| `daily_digest` | Runs every rule | Prioritized findings + Turkish report text |
| `sla_breaches` | Orders past preparation time / past the delivery promise | `critical`/`warning` findings |
| `stock_alerts` | Listings below the stock threshold (sold-out first) | Findings + `threshold` |
| `return_clusters` | Repeated return reasons in the last N days | Findings + `return_rate` |
| `unanswered_reviews` | Negative reviews left unanswered | Findings |
| `price_overview` | Price inconsistencies (above list price, extreme discounts) | Findings + discount summary |
| `list_orders` | Order list (status/date filters) | Order records |
| `list_returns` | Return/claim records | Return records |

Rule definitions, thresholds and example messages: **[docs/rules.md](docs/rules.md)** (Turkish).

```bash
uv run trendyol-mcp tools                # list tools
uv run trendyol-mcp demo --json          # the JSON contract an agent sees
uv run trendyol-mcp --help
```

## Going live

Both marketplaces share one interface; `--source auto` picks whichever credentials it finds.

```bash
cp .env.example .env        # .env is never committed
# Trendyol:    TRENDYOL_SUPPLIER_ID / TRENDYOL_API_KEY / TRENDYOL_API_SECRET
# Hepsiburada: HEPSIBURADA_MERCHANT_ID / HEPSIBURADA_API_KEY (+ HEPSIBURADA_MERCHANT_NAME)
uv run trendyol-mcp check                     # inspect "aktif kaynak" and "yorum okuma"
uv run trendyol-mcp demo --source hepsiburada
uv run trendyol-mcp serve
```

Only `GET` requests are issued (`/integration/order/...`, `/integration/product/...` for Trendyol;
`/orders`, `/returns`, `/listings/merchantid/...` for Hepsiburada). Credentials are read from the
environment and never logged.

What each marketplace can and cannot expose is documented as a **capability matrix** in
`docs/rules.md`: Hepsiburada's merchant API has no product-review endpoint, so the digest skips that
rule and says so with an explicit `not:` line instead of silently reporting nothing. See also
[SECURITY.md](SECURITY.md).

## Architecture

```text
adapters/  →  domain/  →  tools.py  →  server.py (MCP)  ·  cli.py (terminal)
(read-only)    (pure rules)   (JSON)      (read-only tool registration)
```

- `adapters/` maps provider payloads onto normalized models: `FixtureAdapter`, `TrendyolAdapter`,
  `HepsiburadaAdapter`. Auth, retries and field coercion live once in `adapters/http.py` and
  `adapters/parsing.py`, so adding a marketplace is a single-file change.
- `domain/` holds pure functions; every rule takes an explicit `now`, which keeps tests deterministic.
- `render.py` turns findings into Turkish text; the CLI and MCP print the **same** wording.
- Diagram and rationale: [docs/architecture.md](docs/architecture.md) · decision records: [docs/adr/](docs/adr/)

## Quality

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy                              # strict, package + tests + scripts
uv run pytest --cov=trendyol_mcp         # 84 tests, ~91% coverage
```

- **84 tests**: rule boundaries (exact 48/72-hour edges), HTTP mapping for both marketplaces (`respx`),
  the CLI contract, and a **real MCP round trip over stdio** (`tests/test_server_mcp.py`: handshake →
  `tools/list` → `tools/call`).
- CI: Python 3.12 and 3.13 · ruff · ruff format · mypy strict · pytest · credential-free CLI smoke test.
- `server.py` only runs inside a subprocess, so it shows 0% in the coverage report; its live proof is
  the integration test.

## Principles and limits

- **Read-only:** no updates, no dashboard scraping ([ADR-0001](docs/adr/0001-read-only-by-design.md)).
- **Two marketplaces, one contract:** Trendyol and Hepsiburada implement the same read-only protocol;
  data that cannot be read is never silently dropped.
- **Works without credentials:** the sample dataset carries its own time anchor
  ([ADR-0002](docs/adr/0002-fixture-first-testability.md)) → demos and tests are reproducible.
- **Sample data is anonymized:** no real customer, order or price data.
- **Not official:** this project is not affiliated with Trendyol or Hepsiburada; sellers read their own
  data with their own credentials. Trademarks belong to their respective owners.
- **Roadmap:** report delivery, scheduled runs, cross-marketplace stock conflicts → [docs/roadmap.md](docs/roadmap.md).

## Contributing

Issues and PRs are welcome: [CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) ·
[SECURITY.md](SECURITY.md) · changes: [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE) © 2026 acar32furkan-glitch
