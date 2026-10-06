"""CLI contract: exit codes, JSON output and the no-credentials path."""

from __future__ import annotations

import json

import pytest

from trendyol_mcp.cli import main


def test_check_reports_a_ready_environment(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    assert "aktif kaynak      : fixture" in out
    assert "siparis 12" in out
    assert "hazır" in out


def test_check_json_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kayit_sayilari"]["siparis"] == 12
    assert payload["aktif_kaynak"] == "fixture"


def test_demo_prints_the_turkish_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--low-stock", "5", "--sla-hours", "48"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("GÜNLÜK SATICI ÖZETİ")
    assert "1. [KRİTİK]" in out


def test_demo_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 12


def test_global_options_work_on_both_sides_of_the_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--source", "fixture", "check"]) == 0
    first = capsys.readouterr().out
    assert main(["check", "--source", "fixture"]) == 0
    second = capsys.readouterr().out
    assert first == second


def test_tools_listing(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["tools"]) == 0
    out = capsys.readouterr().out
    assert "daily_digest" in out
    assert "sla_breaches" in out


def test_live_source_without_credentials_fails_loudly(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("TRENDYOL_SUPPLIER_ID", "TRENDYOL_API_KEY", "TRENDYOL_API_SECRET"):
        monkeypatch.delenv(name, raising=False)
    assert main(["demo", "--source", "trendyol"]) == 1
    assert "kimlik bilgileri yok" in capsys.readouterr().err.lower()


def test_missing_command_shows_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage: trendyol-mcp" in capsys.readouterr().out


def test_now_flag_pins_the_clock(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--now", "2026-10-06T09:00:00+03:00", "--sla-hours", "100"]) == 0
    out = capsys.readouterr().out
    assert "06.10.2026 09:00" in out
