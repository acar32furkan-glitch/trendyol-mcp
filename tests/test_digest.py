"""Digest snapshot: the bundled dataset must always produce the same prioritized report.

This is the regression net for the whole rule engine: if a rule changes, the expected
``(severity, code)`` sequence below tells the reviewer exactly what moved.
"""

from __future__ import annotations

from pathlib import Path

from trendyol_mcp.adapters import FixtureAdapter
from trendyol_mcp.domain import Thresholds, build_digest
from trendyol_mcp.models import Severity
from trendyol_mcp.render import render_digest_text
from trendyol_mcp.tools import ToolProvider

EXPECTED: list[tuple[Severity, str]] = [
    (Severity.CRITICAL, "HAZIRLIK_GECIKTI"),
    (Severity.CRITICAL, "STOK_YOK"),
    (Severity.CRITICAL, "TESLIM_GECIKTI"),
    (Severity.CRITICAL, "YORUM_CEVAPSIZ"),
    (Severity.WARNING, "FIYAT_LISTEDEN_YUKSEK"),
    (Severity.WARNING, "HAZIRLIK_GECIKTI"),
    (Severity.WARNING, "IADE_KUMESI"),
    (Severity.WARNING, "INDIRIM_ANORMAL"),
    (Severity.WARNING, "STOK_AZ"),
    (Severity.WARNING, "STOK_AZ"),
    (Severity.WARNING, "YORUM_CEVAPSIZ"),
    (Severity.INFO, "IADE_ORANI"),
]


def test_digest_matches_the_snapshot(adapter: FixtureAdapter) -> None:
    digest = build_digest(adapter, now=adapter.reference_time)
    assert [(f.severity, f.code) for f in digest.findings] == EXPECTED
    assert digest.count(Severity.CRITICAL) == 4
    assert digest.count(Severity.WARNING) == 7
    assert digest.count(Severity.INFO) == 1


def test_thresholds_change_the_report(adapter: FixtureAdapter) -> None:
    looser = build_digest(adapter, now=adapter.reference_time, thresholds=Thresholds(low_stock=0, sla_hours=100))
    codes = [f.code for f in looser.findings]
    assert "STOK_AZ" not in codes
    assert "HAZIRLIK_GECIKTI" not in codes


def test_rendered_text_is_a_turkish_report(provider: ToolProvider) -> None:
    text = render_digest_text(provider.digest())
    assert text.startswith("GÜNLÜK SATICI ÖZETİ")
    assert "KRİTİK 4" in text
    assert "UYARI 7" in text
    assert "aksiyon:" in text
    assert "05.10.2026 09:00" in text


def test_clean_dataset_says_nothing_to_do(tmp_path: Path) -> None:
    (tmp_path / "meta.json").write_text(
        '{"reference_time": "2026-10-05T09:00:00+03:00", "marketplace": "test"}', encoding="utf-8"
    )
    for name in ("orders", "returns", "products", "reviews"):
        (tmp_path / f"{name}.json").write_text("[]", encoding="utf-8")
    empty = FixtureAdapter(tmp_path)
    text = render_digest_text(build_digest(empty, now=empty.reference_time))
    assert "aksiyon gerektiren bir şey yok" in text
