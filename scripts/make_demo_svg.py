"""`trendyol-mcp demo` çıktısını SVG "terminal kaydı" olarak üretir.

README'ye gerçek çıktıyı görsel olarak koymak için: elle yazılmış bir ekran görüntüsü yerine,
komutun ürettiği metin her seferinde bu betikle SVG'ye dönüştürülür.

    uv run python scripts/make_demo_svg.py
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from trendyol_mcp.adapters import FixtureAdapter
from trendyol_mcp.cli import resolve_adapter
from trendyol_mcp.render import render_digest_text
from trendyol_mcp.tools import ToolProvider

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "assets" / "demo.svg"

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
CHAR_WIDTH = 7.62
LINE_HEIGHT = 20.0
PADDING_X = 22.0
PADDING_TOP = 54.0
PADDING_BOTTOM = 18.0
MAX_CHARS = 104


def colour_for(line: str) -> str:
    if "[KRİTİK]" in line:
        return "#f87171"
    if "[UYARI]" in line:
        return "#fbbf24"
    if "[BİLGİ]" in line:
        return "#38bdf8"
    if line.startswith(("GÜNLÜK", "Bulgu:", "Kaynak:")):
        return "#e2e8f0"
    return "#cbd5e1"


def wrap(lines: list[str], *, width: int = MAX_CHARS) -> list[str]:
    """Uzun satırları görselde taşmayacak biçimde böl (devam satırı girintili)."""
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= width:
            wrapped.append(line)
            continue
        indent = " " * (line.index(":") + 2 if ":" in line[:14] else 7)
        current = line
        while len(current) > width:
            cut = current.rfind(" ", 0, width)
            cut = cut if cut > 20 else width
            wrapped.append(current[:cut])
            current = indent + current[cut:].lstrip()
        wrapped.append(current)
    return wrapped


def build_svg(lines: list[str], *, title: str) -> str:
    lines = [line[:MAX_CHARS] for line in lines]
    width = max(len(line) for line in lines) * CHAR_WIDTH + PADDING_X * 2
    height = PADDING_TOP + len(lines) * LINE_HEIGHT + PADDING_BOTTOM
    rows = "".join(
        f'<text x="{PADDING_X:.0f}" y="{PADDING_TOP + index * LINE_HEIGHT:.0f}" '
        f'fill="{colour_for(line)}" xml:space="preserve">{escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="trendyol-mcp demo çıktısı">\n'
        f'  <rect width="{width:.0f}" height="{height:.0f}" rx="10" fill="#0b1120"/>\n'
        f'  <rect width="{width:.0f}" height="34" rx="10" fill="#111a2e"/>\n'
        f'  <rect y="24" width="{width:.0f}" height="10" fill="#111a2e"/>\n'
        f'  <circle cx="20" cy="17" r="5.5" fill="#f87171"/>\n'
        f'  <circle cx="38" cy="17" r="5.5" fill="#fbbf24"/>\n'
        f'  <circle cx="56" cy="17" r="5.5" fill="#34d399"/>\n'
        f'  <text x="{PADDING_X + 34:.0f}" y="22" fill="#94a3b8" font-family="{FONT}" '
        f'font-size="13">{escape(title)}</text>\n'
        f'  <g font-family="{FONT}" font-size="13.5">\n    {rows}\n  </g>\n</svg>\n'
    )


def main() -> int:
    adapter = resolve_adapter("fixture")
    assert isinstance(adapter, FixtureAdapter)
    provider = ToolProvider(adapter=adapter)
    text = render_digest_text(provider.digest())
    lines = wrap(text.splitlines())
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(build_svg(lines, title="terminal — trendyol-mcp demo --source fixture"), encoding="utf-8")
    print(f"yazıldı: {TARGET} ({len(lines)} satır)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
