"""Story 62.3 — consumers cite on rows only (spec-build-league-scorecard CAP-3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.core.league_measure import (
    MEASURE_CATALOG_RELATIVE,
    MeasureCiteVerdict,
    load_measure_states,
    parse_measure_catalog,
    validate_measure_cite,
)


def _catalog_snippet(*rows: tuple[str, str]) -> str:
    header = (
        "| id | Dimension | Source (already counted) | State | Notes |\n"
        "|---|---|---|---|---|\n"
    )
    body = "".join(
        f"| `{mid}` | human | source | `{state}` | note |\n" for mid, state in rows
    )
    return header + body


def test_parse_measure_catalog_reads_state_column() -> None:
    states = parse_measure_catalog(
        _catalog_snippet(
            ("warden-verdict", "on"),
            ("ghost-metric", "off"),
            ("retired-metric", "archived"),
        )
    )
    assert states == {
        "warden-verdict": "on",
        "ghost-metric": "off",
        "retired-metric": "archived",
    }


def test_cite_on_allowed() -> None:
    verdict = validate_measure_cite("warden-verdict", repo_root=Path.cwd())
    assert verdict == MeasureCiteVerdict(
        allowed=True, measure_id="warden-verdict", state="on", reason=None
    )


def test_cite_off_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    catalog = tmp_path / MEASURE_CATALOG_RELATIVE
    catalog.parent.mkdir(parents=True)
    catalog.write_text(_catalog_snippet(("warden-verdict", "off")), encoding="utf-8")
    monkeypatch.setattr(
        "pyforge.core.league_measure.load_measure_states",
        lambda repo_root=None: parse_measure_catalog(catalog.read_text(encoding="utf-8")),
    )
    verdict = validate_measure_cite("warden-verdict")
    assert verdict.allowed is False
    assert verdict.state == "off"
    assert verdict.reason is not None and "not on" in verdict.reason


def test_cite_archived_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    catalog = tmp_path / MEASURE_CATALOG_RELATIVE
    catalog.parent.mkdir(parents=True)
    catalog.write_text(_catalog_snippet(("warden-verdict", "archived")), encoding="utf-8")
    monkeypatch.setattr(
        "pyforge.core.league_measure.load_measure_states",
        lambda repo_root=None: parse_measure_catalog(catalog.read_text(encoding="utf-8")),
    )
    verdict = validate_measure_cite("warden-verdict")
    assert verdict.allowed is False
    assert verdict.state == "archived"


def test_cite_unknown_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pyforge.core.league_measure.load_measure_states",
        lambda repo_root=None: {"warden-verdict": "on"},
    )
    verdict = validate_measure_cite("not-in-catalog")
    assert verdict.allowed is False
    assert verdict.state is None
    assert verdict.reason == "unknown measure id"


def test_live_repo_catalog_has_eight_on_rows() -> None:
    states = load_measure_states(Path.cwd())
    assert len(states) == 8  # noqa: PLR2004
    assert all(state == "on" for state in states.values())
