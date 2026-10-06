"""Command line interface.

trendyol-mcp check     # hangi kaynak aktif, kaç kayıt var, kimlik bilgisi bulundu mu
trendyol-mcp demo      # günlük Türkçe özeti yazdır (kimlik bilgisi gerekmez)
trendyol-mcp tools     # ajanlara açılan araçların listesi
trendyol-mcp serve     # MCP sunucusunu stdio üzerinden başlat
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from trendyol_mcp import __version__
from trendyol_mcp.adapters import (
    AdapterError,
    FixtureAdapter,
    HepsiburadaAdapter,
    MarketplaceAdapter,
    TrendyolAdapter,
)
from trendyol_mcp.config import HepsiburadaCredentials, TrendyolCredentials, fixtures_dir
from trendyol_mcp.render import render_digest_text
from trendyol_mcp.tools import TOOL_DESCRIPTIONS, ToolProvider

SOURCES = ("auto", "fixture", "trendyol", "hepsiburada")


def resolve_adapter(source: str, fixtures: Path | None = None) -> MarketplaceAdapter:
    """Pick an adapter: explicit choice wins, ``auto`` prefers live credentials.

    ``auto`` sırası Trendyol → Hepsiburada → örnek veri. Böylece satıcı yalnızca bir
    pazaryerinin anahtarını tanımladıysa doğru kaynak kendiliğinden seçilir.
    """
    directory = fixtures or fixtures_dir()
    if source == "fixture":
        return FixtureAdapter(directory)
    if source == "trendyol":
        return TrendyolAdapter(TrendyolCredentials.from_env())
    if source == "hepsiburada":
        return HepsiburadaAdapter(HepsiburadaCredentials.from_env())
    trendyol = TrendyolCredentials.from_env()
    if trendyol is not None:
        return TrendyolAdapter(trendyol)
    hepsiburada = HepsiburadaCredentials.from_env()
    if hepsiburada is not None:
        return HepsiburadaAdapter(hepsiburada)
    return FixtureAdapter(directory)


def _add_common_options(target: argparse.ArgumentParser, *, suppress_defaults: bool) -> None:
    """Veri kaynağı seçenekleri.

    Kök parser'da varsayılanlarıyla, alt komutlarda ``SUPPRESS`` ile tanımlanır; böylece
    ``trendyol-mcp --source fixture demo`` ve ``trendyol-mcp demo --source fixture``
    biçimlerinin ikisi de aynı sonucu verir.
    """
    default: object = argparse.SUPPRESS if suppress_defaults else None
    target.add_argument(
        "--source",
        choices=SOURCES,
        default=argparse.SUPPRESS if suppress_defaults else "auto",
        help="Veri kaynağı: auto (kimlik bilgisi varsa canlı), fixture (örnek veri), trendyol (canlı).",
    )
    target.add_argument(
        "--fixtures",
        type=Path,
        default=default,
        help="Örnek veri klasörü (varsayılan: examples/data).",
    )
    target.add_argument("--now", default=default, help="Kuralları sabit bir zamana göre çalıştır (ISO 8601).")
    target.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        default=argparse.SUPPRESS if suppress_defaults else False,
        help="Çıktıyı JSON olarak ver.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trendyol-mcp",
        description="Türk pazaryerleri için salt okunur MCP sunucusu (sipariş, iade, stok, SLA, günlük özet).",
    )
    parser.add_argument("--version", action="version", version=f"trendyol-mcp {__version__}")
    _add_common_options(parser, suppress_defaults=False)

    sub = parser.add_subparsers(dest="command")
    for name, help_text in (
        ("check", "Ortamı ve kaynağı doğrula."),
        ("serve", "MCP sunucusunu stdio üzerinden başlat."),
        ("tools", "Ajanlara açılan araçları listele."),
    ):
        child = sub.add_parser(name, help=help_text)
        _add_common_options(child, suppress_defaults=True)

    demo = sub.add_parser("demo", help="Günlük Türkçe aksiyon özetini yazdır.")
    _add_common_options(demo, suppress_defaults=True)
    demo.add_argument("--low-stock", type=int, default=5, help="Stok eşiği (varsayılan 5).")
    demo.add_argument("--sla-hours", type=int, default=48, help="Hazırlık SLA süresi (varsayılan 48 saat).")
    return parser


def _provider(args: argparse.Namespace) -> ToolProvider:
    adapter = resolve_adapter(args.source, args.fixtures)
    now = datetime.fromisoformat(args.now) if args.now else None
    return ToolProvider(adapter=adapter, now=now, fixtures_anchor=adapter.name == "fixture")


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_check(args: argparse.Namespace) -> int:
    provider = _provider(args)
    adapter = provider.adapter
    credentials = TrendyolCredentials.from_env()
    hepsiburada_credentials = HepsiburadaCredentials.from_env()
    orders = adapter.list_orders(limit=500)
    returns = adapter.list_returns(limit=500)
    products = adapter.list_products(limit=500)
    reviews = adapter.list_reviews(limit=500)
    report: dict[str, Any] = {
        "surum": __version__,
        "aktif_kaynak": adapter.name,
        "canli_kimlik_bilgisi": "var" if credentials else "yok (fixture kaynağı kullanılıyor)",
        "kimlik_bilgileri": {
            "trendyol": "var" if credentials else "yok",
            "hepsiburada": "var" if hepsiburada_credentials else "yok",
        },
        "yorum_okuma": "destekli" if adapter.supports_reviews else "bu pazaryerinde uç nokta yok",
        "ornek_veri_klasoru": str(fixtures_dir()),
        "kayit_sayilari": {
            "siparis": len(orders),
            "iade": len(returns),
            "urun": len(products),
            "yorum": len(reviews),
        },
        "degerlendirme_zamani": provider.clock.isoformat(),
    }
    if args.as_json:
        _print_json(report)
        return 0
    counts: dict[str, int] = report["kayit_sayilari"]
    print(f"trendyol-mcp {__version__}")
    print(f"  aktif kaynak      : {report['aktif_kaynak']}")
    print(f"  canlı kimlik      : {report['canli_kimlik_bilgisi']}")
    print(
        "  kimlik bilgileri  : "
        f"trendyol {report['kimlik_bilgileri']['trendyol']}, "
        f"hepsiburada {report['kimlik_bilgileri']['hepsiburada']}"
    )
    print(f"  yorum okuma       : {report['yorum_okuma']}")
    print(f"  örnek veri        : {report['ornek_veri_klasoru']}")
    print(f"  değerlendirme anı : {report['degerlendirme_zamani']}")
    print("  kayıtlar          : " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print("  durum             : hazır ✔ (bir ajan bağlayabilirsiniz: trendyol-mcp serve)")
    return 0


def cmd_tools(args: argparse.Namespace) -> int:
    if args.as_json:
        _print_json(dict(TOOL_DESCRIPTIONS))
        return 0
    print("Ajanlara açılan salt okunur araçlar:")
    width = max(len(name) for name in TOOL_DESCRIPTIONS)
    for name, description in TOOL_DESCRIPTIONS.items():
        print(f"  {name:<{width}}  {description}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    provider = _provider(args)
    if args.as_json:
        _print_json(provider.daily_digest(low_stock=args.low_stock, sla_hours=args.sla_hours))
        return 0
    print(render_digest_text(provider.digest(low_stock=args.low_stock, sla_hours=args.sla_hours)))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from trendyol_mcp.server import run_stdio

    provider = _provider(args)
    run_stdio(provider)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    handlers = {
        "check": cmd_check,
        "demo": cmd_demo,
        "tools": cmd_tools,
        "serve": cmd_serve,
    }
    try:
        return handlers[args.command](args)
    except AdapterError as exc:
        print(f"hata: {exc}", file=sys.stderr)
        return 1
