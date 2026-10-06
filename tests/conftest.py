"""Shared test fixtures.

The bundled dataset under ``examples/data`` is the system under test: it is authored around a
fixed anchor timestamp, so every rule can be asserted deterministically.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.factories import ANCHOR
from trendyol_mcp.adapters import FixtureAdapter
from trendyol_mcp.tools import ToolProvider

FIXTURES: Path = Path(__file__).resolve().parent.parent / "examples" / "data"

__all__ = ["ANCHOR", "FIXTURES", "adapter", "fixtures_dir", "provider"]


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def adapter(fixtures_dir: Path) -> FixtureAdapter:
    return FixtureAdapter(fixtures_dir)


@pytest.fixture
def provider(adapter: FixtureAdapter) -> ToolProvider:
    return ToolProvider(adapter=adapter)
