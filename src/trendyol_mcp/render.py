"""Human-readable rendering.

Kept separate from the rules so the same findings can be printed to a terminal, embedded in
an e-mail or returned through MCP without duplicating wording.
"""

from __future__ import annotations

from trendyol_mcp import __version__
from trendyol_mcp.models import Digest, Severity

_BULLET = {"critical": "[KRİTİK]", "warning": "[UYARI]", "info": "[BİLGİ]"}


def render_digest_text(digest: Digest) -> str:
    """Render the digest as the Turkish morning report a seller would read."""
    lines: list[str] = []
    lines.append(f"GÜNLÜK SATICI ÖZETİ — {digest.generated_at:%d.%m.%Y %H:%M}")
    lines.append(f"Kaynak: {digest.marketplace}  ·  Kural motoru: sürüm {__version__}")
    counts = {s: digest.count(s) for s in (Severity.CRITICAL, Severity.WARNING, Severity.INFO)}
    lines.append(
        f"Bulgu: {len(digest.findings)}  ·  KRİTİK {counts[Severity.CRITICAL]}  ·  "
        f"UYARI {counts[Severity.WARNING]}  ·  BİLGİ {counts[Severity.INFO]}"
    )
    lines.append("-" * 72)

    if not digest.findings:
        lines.append("Bugün aksiyon gerektiren bir şey yok. 🎉")
    else:
        for index, finding in enumerate(digest.findings, start=1):
            marker = _BULLET[finding.severity.value]
            lines.append(f"{index:>2}. {marker} {finding.title_tr}")
            lines.append(f"     durum : {finding.detail_tr}")
            lines.append(f"     aksiyon: {finding.action_tr}")
            if finding.references:
                lines.append(f"     kayıt : {', '.join(finding.references)}")

    if digest.notes:
        lines.append("-" * 72)
        lines.extend(f"not: {note}" for note in digest.notes)
    return "\n".join(lines)


def render_findings_short(findings: list[tuple[str, str]]) -> str:
    """Compact two-column listing used by ``--quiet`` style output."""
    if not findings:
        return "(kayıt yok)"
    width = max(len(left) for left, _ in findings)
    return "\n".join(f"{left:<{width}}  {right}" for left, right in findings)
