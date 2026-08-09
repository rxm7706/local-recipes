"""Unit tests for ``pyforge.doctor.sources.board.gather_check_layout``
(Story 6.5).

Three groups, matching the Code Map:

1. WARN-degrade paths (missing ``check_layout.py``, missing ``data.js``,
   unimportable ``playwright``) -- none need a real browser, and the
   ``playwright``-missing case is forced deterministically via
   ``sys.modules`` so it passes whether or not ``playwright`` happens to be
   installed in whatever environment runs this file.
2. The REUSED, pure ``check()``/``_rows()`` functions, exercised directly
   against synthetic probe-shaped dicts (no browser) -- these load the REAL
   ``docs/dashboard/check_layout.py`` via ``board._load_check_layout`` (the
   same dynamic-import path production code uses), because the whole point
   of the port is that this module's geometry assertions are REUSED
   verbatim, not reimplemented; skipped if this checkout has no
   ``docs/dashboard/`` (e.g. a stripped-down source distribution).
3. One ``pytest.importorskip("playwright")``-gated end-to-end smoke test --
   skips cleanly in this package's own pixi env, which does not install
   ``playwright`` (Boundaries).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import board

_REPO_ROOT = Path(__file__).resolve().parents[6]
_HAVE_REAL_DASHBOARD = (_REPO_ROOT / "docs" / "dashboard" / "check_layout.py").is_file()


def _write_minimal_check_layout(target: Path) -> None:
    """A trivial stand-in module -- enough for ``_load_check_layout`` to
    succeed; the WARN paths under test never reach ``HERE``/``_serve``/
    ``check()``, so this does not need to be the real script."""
    path = target / "docs" / "dashboard" / "check_layout.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("HERE = None\n", encoding="utf-8")


def _touch_data_js(target: Path) -> None:
    path = target / "docs" / "dashboard" / "data.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("window.DASHBOARD_DATA = {};\n", encoding="utf-8")


# --- WARN-degrade paths (no browser needed) ---------------------------------


def test_missing_check_layout_module_degrades_to_warn(tmp_path: Path) -> None:
    # deliberately no docs/dashboard/check_layout.py at all
    findings = board.gather_check_layout(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHECK_LAYOUT
    assert finding.check == "console-bar-layout"
    assert finding.status is DoctorStatus.WARN


def test_missing_data_js_degrades_to_warn(tmp_path: Path) -> None:
    _write_minimal_check_layout(tmp_path)
    # deliberately no docs/dashboard/data.js

    findings = board.gather_check_layout(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "data.js" in finding.message
    assert "dashboard-gen" in finding.message


def test_playwright_not_importable_degrades_to_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forced deterministically via ``sys.modules`` rather than relying on
    this environment happening to lack ``playwright`` -- the test must pass
    the same way whether or not it is installed."""
    _write_minimal_check_layout(tmp_path)
    _touch_data_js(tmp_path)
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    findings = board.gather_check_layout(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHECK_LAYOUT
    assert finding.status is DoctorStatus.WARN
    assert "playwright" in finding.message


def test_never_raises_when_check_layout_module_itself_is_broken(tmp_path: Path) -> None:
    """A syntax/runtime error in the dynamically-loaded file must degrade to
    WARN, not propagate -- this module's own house rule."""
    path = tmp_path / "docs" / "dashboard" / "check_layout.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("raise RuntimeError('boom')\n", encoding="utf-8")

    findings = board.gather_check_layout(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- check()/_rows() re-exercised directly, synthetic geometry, no browser --


@pytest.mark.skipif(not _HAVE_REAL_DASHBOARD,
                     reason="real docs/dashboard/check_layout.py not present in this checkout")
class TestReusedGeometryFunctions:
    @staticmethod
    def _clm():
        return board._load_check_layout(_REPO_ROOT)

    def test_clean_layout_reports_no_findings(self) -> None:
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 0, "b": 34, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        assert clm.check(1000, m, f"{clm.DESIGN_SIZE}px") == []

    def test_overlap_is_reported_naming_the_chips_and_offset(self) -> None:
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 250, "t": 0, "b": 34, "cx": 127.5,
                                "need": 200, "have": 245},
                "#chip-run": {"l": 200, "r": 395, "t": 0, "b": 34, "cx": 297.5,
                               "need": 150, "have": 195},
            },
        }
        findings = clm.check(1000, m, f"{clm.DESIGN_SIZE}px")
        assert any(
            "#chip-ship" in f and "#chip-run" in f and "OVERLAP" in f and "50.0px" in f
            for f in findings
        )

    def test_clipped_chip_is_reported(self) -> None:
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 0, "b": 34, "cx": 347.5,
                               "need": 300, "have": 95},
            },
        }
        findings = clm.check(1000, m, f"{clm.DESIGN_SIZE}px")
        assert any("CLIPPED" in f and "#chip-run" in f for f in findings)

    def test_chip_escaping_the_bar_is_reported(self) -> None:
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": -20, "r": 100, "t": 0, "b": 34, "cx": 40,
                                "need": 90, "have": 120},
                "#chip-run": {"l": 300, "r": 395, "t": 0, "b": 34, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        findings = clm.check(1000, m, f"{clm.DESIGN_SIZE}px")
        assert any("escapes the bar" in f and "#chip-ship" in f for f in findings)

    def test_bar_wrapped_to_two_rows_at_design_size_is_reported(self) -> None:
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 68},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 40, "b": 74, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        findings = clm.check(1000, m, f"{clm.DESIGN_SIZE}px")
        assert any("wrapped to 2 rows" in f for f in findings)

    def test_wrapping_under_font_pressure_above_design_size_is_not_flagged(self) -> None:
        """The one-row assertion is scoped to DESIGN_SIZE only -- wrapping
        under font pressure at a LARGER size is the intended degradation."""
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 68},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 40, "b": 74, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        findings = clm.check(1000, m, "24px")
        assert not any("wrapped to" in f for f in findings)

    def test_narrow_width_stacked_rows_do_not_false_positive_on_overlap(self) -> None:
        """Below BREAKPOINT, horizontal ranges legitimately coincide once
        stacked into separate rows -- the docstring's own false-positive
        rationale."""
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 68},
            "chips": {
                "#chip-ship": {"l": 5, "r": 300, "t": 0, "b": 34, "cx": 152.5,
                                "need": 250, "have": 295},
                "#chip-run": {"l": 5, "r": 300, "t": 40, "b": 74, "cx": 152.5,
                               "need": 250, "have": 295},
            },
        }
        findings = clm.check(clm.NARROW[0], m, f"{clm.DESIGN_SIZE}px")
        assert findings == []

    def test_missing_chip_is_reported_and_short_circuits_other_assertions(self) -> None:
        clm = self._clm()
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
            },
        }
        findings = clm.check(1000, m, f"{clm.DESIGN_SIZE}px")
        assert len(findings) == 1
        assert "#chip-run" in findings[0]
        assert "absent from the DOM" in findings[0]

    def test_rows_groups_chips_by_vertical_overlap(self) -> None:
        clm = self._clm()
        chips = {
            "#chip-ship": {"t": 0, "b": 34},
            "#chip-run": {"t": 40, "b": 74},
        }
        assert clm._rows(chips) == [["#chip-ship"], ["#chip-run"]]

    def test_rows_groups_vertically_overlapping_chips_together(self) -> None:
        clm = self._clm()
        chips = {
            "#chip-ship": {"t": 0, "b": 34},
            "#chip-run": {"t": 10, "b": 44},
        }
        assert clm._rows(chips) == [["#chip-ship", "#chip-run"]]


# --- End-to-end browser smoke test -------------------------------------------


def test_gather_check_layout_end_to_end_smoke() -> None:
    """Skips cleanly (never errors the suite) in an environment without
    ``playwright`` -- e.g. this package's own pixi env (Boundaries)."""
    pytest.importorskip("playwright")
    if not _HAVE_REAL_DASHBOARD:
        pytest.skip("real docs/dashboard not present in this checkout")

    findings = board.gather_check_layout(_REPO_ROOT)

    assert findings
    assert all(f.source is Source.CHECK_LAYOUT for f in findings)
    assert all(
        f.status in (DoctorStatus.OK, DoctorStatus.FAIL, DoctorStatus.WARN) for f in findings
    )
