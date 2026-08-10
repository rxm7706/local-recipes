"""Unit tests for ``pyforge.doctor.sources.board.gather_check_layout``
(Story 6.5; Story 6.9 fix: the geometry assertions moved in as permanent
code -- see ``board.py``'s own ``=== gather_check_layout ===`` section
header for why).

Three groups, matching the Code Map:

1. WARN-degrade paths (missing ``data.js``, unimportable ``playwright``) --
   none need a real browser, and the ``playwright``-missing case is forced
   deterministically via ``sys.modules`` so it passes whether or not
   ``playwright`` happens to be installed in whatever environment runs this
   file. There is no longer a "missing/broken ``check_layout.py``" WARN
   path to test here: Story 6.9 ported the assertions in as permanent code,
   so there is nothing left to fail to load -- ``test_still_works_when_
   check_layout_py_is_absent_from_disk`` below pins that directly.
2. The geometry functions (``_check_layout_geometry``/``_layout_chip_rows``,
   ported verbatim from the origin's own ``check()``/``_rows()``), exercised
   directly against synthetic probe-shaped dicts (no browser). They are now
   PERMANENT module-level code, unconditionally present -- no skip guard,
   no dynamic load.
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
from pyforge.doctor.verdict import exit_code_for

# Guarded, like `test_check_speed_budget.py`'s own (review finding): at module
# scope a bare `parents[6]` IndexError from a shallower-than-7-levels layout
# (e.g. an extracted sdist) is a COLLECTION error for this whole file instead
# of the skip this module's docstring promises.
try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
# What the end-to-end smoke test actually needs is a real board to SERVE and
# MEASURE (data.js + index.html) -- not check_layout.py, which Story 6.9
# retired and which this module no longer reads at all.
_HAVE_REAL_DASHBOARD = bool(
    _REPO_ROOT
    and (_REPO_ROOT / "docs" / "dashboard" / "data.js").is_file()
    and (_REPO_ROOT / "docs" / "dashboard" / "index.html").is_file()
)


def _touch_data_js(target: Path) -> None:
    path = target / "docs" / "dashboard" / "data.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("window.DASHBOARD_DATA = {};\n", encoding="utf-8")


# --- WARN-degrade paths (no browser needed) ---------------------------------


def test_missing_data_js_degrades_to_warn(tmp_path: Path) -> None:
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
    _touch_data_js(tmp_path)
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    findings = board.gather_check_layout(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHECK_LAYOUT
    assert finding.status is DoctorStatus.WARN
    assert "playwright" in finding.message


def test_still_works_when_check_layout_py_is_absent_from_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE Story 6.9 regression, pinned directly: before the fix,
    ``gather_check_layout`` dynamically loaded
    ``target/docs/dashboard/check_layout.py`` to reuse its assertions, so a
    target lacking that file (every target, once the origin script retired)
    degraded to ONE permanent WARN forever, in every environment -- the
    real layout verdict became unreachable. Now the assertions are
    permanent code, so an absent ``check_layout.py`` must not appear in the
    WARN path at all: with ``data.js`` present and ``playwright`` forced
    unavailable (so this stays browser-free and deterministic), the WARN
    must be about playwright, never about a missing/unloadable
    ``check_layout.py``."""
    _touch_data_js(tmp_path)
    assert not (tmp_path / "docs" / "dashboard" / "check_layout.py").exists()
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    findings = board.gather_check_layout(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert "playwright" in findings[0].message
    assert "check_layout.py" not in findings[0].message
    assert "could not be evaluated here" not in findings[0].message


# --- geometry functions, permanent code, no skip guard -----------------------


class TestGeometryFunctions:
    def test_clean_layout_reports_no_findings(self) -> None:
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 0, "b": 34, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        assert board._check_layout_geometry(1000, m, f"{board._LAYOUT_DESIGN_SIZE}px") == []

    def test_overlap_is_reported_naming_the_chips_and_offset(self) -> None:
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 250, "t": 0, "b": 34, "cx": 127.5,
                                "need": 200, "have": 245},
                "#chip-run": {"l": 200, "r": 395, "t": 0, "b": 34, "cx": 297.5,
                               "need": 150, "have": 195},
            },
        }
        findings = board._check_layout_geometry(1000, m, f"{board._LAYOUT_DESIGN_SIZE}px")
        assert any(
            "#chip-ship" in f and "#chip-run" in f and "OVERLAP" in f and "50.0px" in f
            for f in findings
        )

    def test_clipped_chip_is_reported(self) -> None:
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 0, "b": 34, "cx": 347.5,
                               "need": 300, "have": 95},
            },
        }
        findings = board._check_layout_geometry(1000, m, f"{board._LAYOUT_DESIGN_SIZE}px")
        assert any("CLIPPED" in f and "#chip-run" in f for f in findings)

    def test_chip_escaping_the_bar_is_reported(self) -> None:
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": -20, "r": 100, "t": 0, "b": 34, "cx": 40,
                                "need": 90, "have": 120},
                "#chip-run": {"l": 300, "r": 395, "t": 0, "b": 34, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        findings = board._check_layout_geometry(1000, m, f"{board._LAYOUT_DESIGN_SIZE}px")
        assert any("escapes the bar" in f and "#chip-ship" in f for f in findings)

    def test_bar_wrapped_to_two_rows_at_design_size_is_reported(self) -> None:
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 68},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 40, "b": 74, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        findings = board._check_layout_geometry(1000, m, f"{board._LAYOUT_DESIGN_SIZE}px")
        assert any("wrapped to 2 rows" in f for f in findings)

    def test_wrapping_under_font_pressure_above_design_size_is_not_flagged(self) -> None:
        """The one-row assertion is scoped to DESIGN_SIZE only -- wrapping
        under font pressure at a LARGER size is the intended degradation."""
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 68},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
                "#chip-run": {"l": 300, "r": 395, "t": 40, "b": 74, "cx": 347.5,
                               "need": 90, "have": 95},
            },
        }
        findings = board._check_layout_geometry(1000, m, "24px")
        assert not any("wrapped to" in f for f in findings)

    def test_narrow_width_stacked_rows_do_not_false_positive_on_overlap(self) -> None:
        """Below BREAKPOINT, horizontal ranges legitimately coincide once
        stacked into separate rows -- the docstring's own false-positive
        rationale."""
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 68},
            "chips": {
                "#chip-ship": {"l": 5, "r": 300, "t": 0, "b": 34, "cx": 152.5,
                                "need": 250, "have": 295},
                "#chip-run": {"l": 5, "r": 300, "t": 40, "b": 74, "cx": 152.5,
                               "need": 250, "have": 295},
            },
        }
        findings = board._check_layout_geometry(
            board._LAYOUT_NARROW[0], m, f"{board._LAYOUT_DESIGN_SIZE}px"
        )
        assert findings == []

    def test_missing_chip_is_reported_and_short_circuits_other_assertions(self) -> None:
        m = {
            "bar": {"l": 0, "r": 400, "cx": 200, "h": 34},
            "chips": {
                "#chip-ship": {"l": 5, "r": 100, "t": 0, "b": 34, "cx": 52.5,
                                "need": 90, "have": 95},
            },
        }
        findings = board._check_layout_geometry(1000, m, f"{board._LAYOUT_DESIGN_SIZE}px")
        assert len(findings) == 1
        assert "#chip-run" in findings[0]
        assert "absent from the DOM" in findings[0]

    def test_rows_groups_chips_by_vertical_overlap(self) -> None:
        chips = {
            "#chip-ship": {"t": 0, "b": 34},
            "#chip-run": {"t": 40, "b": 74},
        }
        assert board._layout_chip_rows(chips) == [["#chip-ship"], ["#chip-run"]]

    def test_rows_groups_vertically_overlapping_chips_together(self) -> None:
        chips = {
            "#chip-ship": {"t": 0, "b": 34},
            "#chip-run": {"t": 10, "b": 44},
        }
        assert board._layout_chip_rows(chips) == [["#chip-ship", "#chip-run"]]


# --- End-to-end browser smoke test -------------------------------------------


def test_gather_check_layout_end_to_end_smoke() -> None:
    """Skips cleanly (never errors the suite) in an environment without
    ``playwright`` -- e.g. this package's own pixi env (Boundaries)."""
    pytest.importorskip("playwright")
    if not _HAVE_REAL_DASHBOARD:
        pytest.skip("real docs/dashboard (data.js + index.html) not present in this checkout")

    findings = board.gather_check_layout(_REPO_ROOT)

    assert findings
    assert all(f.source is Source.CHECK_LAYOUT for f in findings)
    assert all(
        f.status in (DoctorStatus.OK, DoctorStatus.FAIL, DoctorStatus.WARN) for f in findings
    )


# --- _run_check_layout, driven through its own seam --------------------------
#
# `_run_check_layout(target, sync_playwright)` reads the layout grid/probe/
# assertion names as this module's OWN module-level attributes (Story 6.9;
# previously a dynamically-loaded module passed in as a parameter) -- so the
# orchestration is still fully drivable with stubs and no `playwright`
# installed, via `monkeypatch.setattr(board, "_LAYOUT_WIDE", ...)` etc.
# instead of a `clm` argument. Two review passes on the pre-6.9 shape found
# four real defects living in exactly this orchestration; every one of them
# is still reproduced through the stubs below.


class _FakePage:
    def __init__(self, width: int, script: _Script) -> None:
        self.width, self.script = width, script

    def goto(self, *_a, **_k) -> None:
        self.script.on_goto(self.width)

    def wait_for_timeout(self, *_a) -> None:
        pass

    def evaluate(self, _code, *_a):
        return self.script.probe(self.width)

    def close(self) -> None:
        pass


class _FakeBrowser:
    def __init__(self, script: _Script) -> None:
        self.script = script

    def new_page(self, viewport):
        return _FakePage(viewport["width"], self.script)

    def close(self) -> None:
        self.script.on_close()


class _FakeChromium:
    def __init__(self, script: _Script) -> None:
        self.script = script

    def launch(self, **_k):
        if self.script.no_browser:
            raise RuntimeError("no chromium here")
        return _FakeBrowser(self.script)


class _FakePlaywright:
    def __init__(self, script: _Script) -> None:
        self.chromium = _FakeChromium(script)

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


class _Script:
    """A scripted browser: which widths flake, whether close() blows up."""

    def __init__(
        self,
        *,
        flaky_widths: tuple[int, ...] = (),
        blank_widths: tuple[int, ...] = (),
        close_raises: bool = False,
        no_browser: bool = False,
    ) -> None:
        self.flaky_widths = flaky_widths
        self.blank_widths = blank_widths
        self.close_raises = close_raises
        self.no_browser = no_browser

    def on_goto(self, width: int) -> None:
        if width in self.flaky_widths:
            raise TimeoutError("Timeout 20000ms exceeded")

    def probe(self, width: int):
        return None if width in self.blank_widths else {"measured": True}

    def on_close(self) -> None:
        if self.close_raises:
            raise RuntimeError("browser process died on close")

    def __call__(self):
        return _FakePlaywright(self)


class _FakeHttpd:
    def __init__(self) -> None:
        self.shutdown_called = self.closed = False

    def shutdown(self) -> None:
        self.shutdown_called = True

    def server_close(self) -> None:
        self.closed = True


class _StubLayoutModule:
    """The layout grid/probe/assertion seam ``_run_check_layout`` reads --
    applied onto ``board``'s own module-level names via ``_apply`` below,
    standing in for what used to be a dynamically loaded module's attribute
    surface."""

    WIDE = (1400, 1100)
    NARROW = (700,)
    PRESSURES = (11, 13)
    APPLY = PROBE = "() => null"

    def __init__(self, findings: tuple[str, ...] = ()) -> None:
        self._findings = findings
        self.httpd = _FakeHttpd()

    def _serve(self, _here):
        return self.httpd, 9999

    def check(self, _width, _m, _name) -> list[str]:
        return list(self._findings)


def _apply(monkeypatch: pytest.MonkeyPatch, clm: _StubLayoutModule) -> None:
    monkeypatch.setattr(board, "_LAYOUT_WIDE", clm.WIDE)
    monkeypatch.setattr(board, "_LAYOUT_NARROW", clm.NARROW)
    monkeypatch.setattr(board, "_LAYOUT_PRESSURES", clm.PRESSURES)
    monkeypatch.setattr(board, "_LAYOUT_APPLY", clm.APPLY)
    monkeypatch.setattr(board, "_LAYOUT_PROBE", clm.PROBE)
    monkeypatch.setattr(board, "_check_layout_geometry", clm.check)
    monkeypatch.setattr(board, "_serve_layout_dir", clm._serve)


def _run(monkeypatch: pytest.MonkeyPatch, clm: _StubLayoutModule, script: _Script):
    """Through ``degrade_on_exception``, exactly as ``gather_check_layout``
    calls it -- so a test can tell "returned a WARN" from "raised and got
    wrapped"."""
    _apply(monkeypatch, clm)
    return board.degrade_on_exception(
        Source.CHECK_LAYOUT,
        "console-bar-layout",
        lambda: board._run_check_layout(Path("/t"), script),
    )


def test_a_clean_sweep_reports_one_ok_over_the_full_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _run(monkeypatch, _StubLayoutModule(), _Script())

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert "6 measurement(s)" in findings[0].message  # 3 widths x 2 pressures
    assert findings[0].evidence["measured"] == 6


def test_a_real_layout_defect_reports_fail_per_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _run(
        monkeypatch, _StubLayoutModule(("overlap: chip A over chip B",)), _Script()
    )

    assert {f.status for f in findings} == {DoctorStatus.FAIL}
    assert all("overlap" in f.message for f in findings)


def test_one_flaky_width_warns_and_does_not_red_a_clean_board(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`exit_code_for` maps FAIL to exit 2 and WARN to 0. Reporting a
    `networkidle` timeout -- the EXPECTED failure mode at a 20s budget -- as a
    layout FAIL turned the gate red on a board that measured clean everywhere
    it could be measured. Reproduced live."""
    findings = _run(monkeypatch, _StubLayoutModule(), _Script(flaky_widths=(1400,)))

    warns = [f for f in findings if f.status is DoctorStatus.WARN]
    assert len(warns) == 1
    assert "w=1400: could not be measured" in warns[0].message
    assert not [f for f in findings if f.status is DoctorStatus.FAIL], (
        f"a browser flake was reported as a layout defect: {findings}"
    )
    assert exit_code_for(findings) == 0

    ok = [f for f in findings if f.status is DoctorStatus.OK]
    assert len(ok) == 1
    assert "could not be measured" in ok[0].message, (
        "the OK finding must not claim a grid it did not measure"
    )


def test_a_flaky_width_never_hides_a_real_defect_at_another_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _run(
        monkeypatch,
        _StubLayoutModule(("overlap: chip A over chip B",)),
        _Script(flaky_widths=(1400,)),
    )

    assert [f.message for f in findings if f.status is DoctorStatus.FAIL], (
        f"a real defect vanished behind a flake: {findings}"
    )
    assert exit_code_for(findings) == 2


def test_a_browser_that_dies_on_close_does_not_erase_the_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The per-width guard closed this masking hole inside the loop; the
    unguarded `finally: browser.close()` reopened it one frame up, where a
    raise put every already-collected FAIL back behind one whole-gather WARN.
    Reproduced live."""
    findings = _run(
        monkeypatch,
        _StubLayoutModule(("overlap: chip A over chip B",)),
        _Script(close_raises=True),
    )

    assert {f.status for f in findings} == {DoctorStatus.FAIL}, (
        f"a failed teardown erased the verdict: {findings}"
    )
    assert exit_code_for(findings) == 2


def test_the_http_server_is_always_shut_down_and_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`shutdown()` only stops serve_forever's loop -- without
    `server_close()` the listening socket leaks one fd per call."""
    clm = _StubLayoutModule()
    _run(monkeypatch, clm, _Script(close_raises=True))

    assert clm.httpd.shutdown_called
    assert clm.httpd.closed


def test_when_no_width_could_be_measured_the_reasons_survive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returning only "the bar never rendered at any width" discarded every
    collected diagnostic AND asserted a cause never observed: when the page
    failed to LOAD, whether the bar would have rendered is precisely what is
    unknown."""
    findings = _run(monkeypatch, _StubLayoutModule(), _Script(flaky_widths=(1400, 1100, 700)))

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "Timeout 20000ms exceeded" in findings[0].message
    assert "w=1400" in findings[0].message and "w=700" in findings[0].message


def test_a_bar_that_never_renders_anywhere_is_unknown_but_keeps_its_reasons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`measured == 0` is the original's own UNKNOWN (`exit 2`), so WARN is
    the faithful status -- but the `.cbstatus not found` lines it collected on
    the way there must not be thrown away with it."""
    findings = _run(monkeypatch, _StubLayoutModule(), _Script(blank_widths=(1400, 1100, 700)))

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "did not render" in findings[0].message
    assert "w=1400" in findings[0].message and "w=700" in findings[0].message


def test_a_bar_that_fails_to_render_at_only_one_width_stays_a_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other direction of the same split: once something WAS measured,
    `.cbstatus not found` is the ORIGINAL's own finding text for a page that
    loaded and did not render, so it must not be softened to WARN along with
    the flakes."""
    findings = _run(monkeypatch, _StubLayoutModule(), _Script(blank_widths=(700,)))

    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert len(fails) == 2  # one per font-pressure step at the blank width
    assert all("did not render" in f.message for f in fails)
    assert exit_code_for(findings) == 2


def test_no_usable_chromium_degrades_to_exactly_one_warn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    findings = _run(monkeypatch, _StubLayoutModule(), _Script(no_browser=True))

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "no usable chromium" in findings[0].message


# --- adversarial-review regressions (2026-08-09, fourth pass) ----------------


class _FakePageThatDiesOnClose(_FakePage):
    def close(self) -> None:
        raise RuntimeError("page close blew up")


def test_a_page_that_dies_on_close_is_not_reported_as_unmeasured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`page.close()` sat INSIDE the per-width `try`, whose `except` appends to
    `unmeasured` -- so a fully-measured width was reported "could not be
    measured" AND counted in `measured`, producing a self-contradictory OK
    ("6 measurement(s): 3 width(s) x 2 steps; 3 width(s) could not be
    measured"). Its two sibling teardowns were already suppressed. Reproduced
    live."""
    monkeypatch.setattr(
        _FakeBrowser,
        "new_page",
        lambda self, viewport: _FakePageThatDiesOnClose(viewport["width"], self.script),
    )

    findings = _run(monkeypatch, _StubLayoutModule(), _Script())

    assert [f.status for f in findings] == [DoctorStatus.OK], (
        f"a failed page teardown was reported as a failed measurement: "
        f"{[(f.status.value, f.message) for f in findings]}"
    )
    assert "could not be measured" not in findings[0].message
    assert findings[0].evidence["measured"] == 6


def test_the_served_directory_is_the_target_not_some_other_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`_run_check_layout` must serve `target/docs/dashboard`, not any other
    directory. Pre-Story-6.9, the loaded `check_layout.py`'s own `HERE`
    (`Path(__file__).resolve().parent`) was a live hazard whenever the file
    was symlinked or shared: the gather validated one repo's data.js and
    measured a DIFFERENT repo's dashboard (reproduced live). Story 6.9
    removed that indirection entirely -- there is no loaded module's `HERE`
    to prefer by mistake any more -- so this now just pins the one directory
    `_serve_layout_dir` is actually called with."""
    clm = _StubLayoutModule()
    served: list[Path] = []
    clm._serve = lambda here: (served.append(here), (clm.httpd, 9999))[1]

    _run(monkeypatch, clm, _Script())

    assert served == [Path("/t") / "docs" / "dashboard"], (
        f"the gather measured a directory other than its target: {served}"
    )


def test_a_check_layout_geometry_call_that_exits_degrades_to_warn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`SystemExit` raised from inside the per-width block is neither caught
    by the per-width `except Exception` nor by `degrade_on_exception` --
    kept as defense-in-depth against playwright's own internals (Story 6.9;
    previously against a dynamically-loaded file's own `check()`, which no
    longer exists).

    Doubles as the pin on `measured`'s meaning: it is incremented AFTER
    `_check_layout_geometry` returns, so a call that never completes cannot
    be counted toward the OK message's "console bar edges held, no overlap"
    claim.
    """
    clm = _StubLayoutModule()

    def _exit(*_a, **_k):
        raise SystemExit("boom from check()")

    clm.check = _exit

    findings = _run(monkeypatch, clm, _Script())  # must not raise

    assert [f.status for f in findings] == [DoctorStatus.WARN], (
        f"an evaluation that never ran was reported as a clean grid: "
        f"{[(f.status.value, f.message) for f in findings]}"
    )
    assert "boom from check()" in findings[0].message
