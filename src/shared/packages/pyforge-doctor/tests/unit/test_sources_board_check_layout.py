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
from pyforge.doctor.verdict import exit_code_for

# Guarded, like `test_check_speed_budget.py`'s own (review finding): at module
# scope a bare `parents[6]` IndexError from a shallower-than-7-levels layout
# (e.g. an extracted sdist) is a COLLECTION error for this whole file instead
# of the skip this module's docstring promises.
try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_HAVE_REAL_DASHBOARD = bool(
    _REPO_ROOT and (_REPO_ROOT / "docs" / "dashboard" / "check_layout.py").is_file()
)


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


# --- _run_check_layout, driven through its own seam --------------------------
#
# `_run_check_layout(target, clm, sync_playwright)` already takes both the
# layout module and the browser factory as PARAMETERS, so the orchestration --
# the only genuinely new code in this port -- is fully drivable with stubs and
# no `playwright` installed. A previous review pass deferred this coverage as
# needing "a fake-browser seam or an opt-in CI lane"; the seam was already
# there. Two review passes found four real defects living in exactly this
# uncovered region, every one of them reproduced through the stubs below.


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
    """Stands in for the dynamically loaded `check_layout.py`, exposing only
    the attribute surface `_run_check_layout` actually consumes."""

    WIDE = (1400, 1100)
    NARROW = (700,)
    PRESSURES = (11, 13)
    APPLY = PROBE = "() => null"
    HERE = Path(".")

    def __init__(self, findings: tuple[str, ...] = ()) -> None:
        self._findings = findings
        self.httpd = _FakeHttpd()

    def _serve(self, _here):
        return self.httpd, 9999

    def check(self, _width, _m, _name) -> list[str]:
        return list(self._findings)


def _run(clm: _StubLayoutModule, script: _Script):
    """Through `degrade_on_exception`, exactly as `gather_check_layout` calls
    it -- so a test can tell "returned a WARN" from "raised and got wrapped"."""
    return board.degrade_on_exception(
        Source.CHECK_LAYOUT,
        "console-bar-layout",
        lambda: board._run_check_layout(Path("/t"), clm, script),
    )


def test_a_clean_sweep_reports_one_ok_over_the_full_grid() -> None:
    findings = _run(_StubLayoutModule(), _Script())

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert "6 measurement(s)" in findings[0].message  # 3 widths x 2 pressures
    assert findings[0].evidence["measured"] == 6


def test_a_real_layout_defect_reports_fail_per_measurement() -> None:
    findings = _run(_StubLayoutModule(("overlap: chip A over chip B",)), _Script())

    assert {f.status for f in findings} == {DoctorStatus.FAIL}
    assert all("overlap" in f.message for f in findings)


def test_one_flaky_width_warns_and_does_not_red_a_clean_board() -> None:
    """`exit_code_for` maps FAIL to exit 2 and WARN to 0. Reporting a
    `networkidle` timeout -- the EXPECTED failure mode at a 20s budget -- as a
    layout FAIL turned the gate red on a board that measured clean everywhere
    it could be measured. Reproduced live."""
    findings = _run(_StubLayoutModule(), _Script(flaky_widths=(1400,)))

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


def test_a_flaky_width_never_hides_a_real_defect_at_another_width() -> None:
    findings = _run(
        _StubLayoutModule(("overlap: chip A over chip B",)), _Script(flaky_widths=(1400,))
    )

    assert [f.message for f in findings if f.status is DoctorStatus.FAIL], (
        f"a real defect vanished behind a flake: {findings}"
    )
    assert exit_code_for(findings) == 2


def test_a_browser_that_dies_on_close_does_not_erase_the_findings() -> None:
    """The per-width guard closed this masking hole inside the loop; the
    unguarded `finally: browser.close()` reopened it one frame up, where a
    raise put every already-collected FAIL back behind one whole-gather WARN.
    Reproduced live."""
    findings = _run(
        _StubLayoutModule(("overlap: chip A over chip B",)), _Script(close_raises=True)
    )

    assert {f.status for f in findings} == {DoctorStatus.FAIL}, (
        f"a failed teardown erased the verdict: {findings}"
    )
    assert exit_code_for(findings) == 2


def test_the_http_server_is_always_shut_down_and_closed() -> None:
    """`shutdown()` only stops serve_forever's loop -- without
    `server_close()` the listening socket leaks one fd per call."""
    clm = _StubLayoutModule()
    _run(clm, _Script(close_raises=True))

    assert clm.httpd.shutdown_called
    assert clm.httpd.closed


def test_when_no_width_could_be_measured_the_reasons_survive() -> None:
    """Returning only "the bar never rendered at any width" discarded every
    collected diagnostic AND asserted a cause never observed: when the page
    failed to LOAD, whether the bar would have rendered is precisely what is
    unknown."""
    findings = _run(_StubLayoutModule(), _Script(flaky_widths=(1400, 1100, 700)))

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "Timeout 20000ms exceeded" in findings[0].message
    assert "w=1400" in findings[0].message and "w=700" in findings[0].message


def test_a_bar_that_never_renders_anywhere_is_unknown_but_keeps_its_reasons() -> None:
    """`measured == 0` is the original's own UNKNOWN (`exit 2`), so WARN is
    the faithful status -- but the `.cbstatus not found` lines it collected on
    the way there must not be thrown away with it."""
    findings = _run(_StubLayoutModule(), _Script(blank_widths=(1400, 1100, 700)))

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "did not render" in findings[0].message
    assert "w=1400" in findings[0].message and "w=700" in findings[0].message


def test_a_bar_that_fails_to_render_at_only_one_width_stays_a_fail() -> None:
    """The other direction of the same split: once something WAS measured,
    `.cbstatus not found` is the ORIGINAL's own finding text for a page that
    loaded and did not render, so it must not be softened to WARN along with
    the flakes."""
    findings = _run(_StubLayoutModule(), _Script(blank_widths=(700,)))

    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert len(fails) == 2  # one per font-pressure step at the blank width
    assert all("did not render" in f.message for f in fails)
    assert exit_code_for(findings) == 2


def test_no_usable_chromium_degrades_to_exactly_one_warn() -> None:
    findings = _run(_StubLayoutModule(), _Script(no_browser=True))

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "no usable chromium" in findings[0].message


def test_check_layout_loader_gets_the_same_hygiene_as_its_sibling(
    tmp_path: Path,
) -> None:
    """The two dynamic loaders had drifted: only `_load_dashboard_generate`
    snapshotted `sys.path` and cleaned `sys.modules` on failure. They now
    share one helper, so this pins that `_load_check_layout` really routes
    through it rather than re-growing its own copy."""
    path = tmp_path / "docs" / "dashboard" / "check_layout.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import sys\nsys.path.insert(0, '/tmp/EVIL-CHECK-LAYOUT-PROBE')\n"
        "raise RuntimeError('boom')\n",
        encoding="utf-8",
    )
    before = list(sys.path)

    with pytest.raises(RuntimeError):
        board._load_check_layout(tmp_path)

    assert sys.path == before
    assert "_doctor_board_check_layout" not in sys.modules


def test_a_check_layout_that_exits_at_import_degrades_to_warn(tmp_path: Path) -> None:
    """`SystemExit` is a BaseException, so `degrade_on_exception` never
    catches it and `gather_check_layout`'s own `except Exception` misses it
    too -- it escaped the gather entirely."""
    path = tmp_path / "docs" / "dashboard" / "check_layout.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("import sys\nsys.exit('boom')\n", encoding="utf-8")

    findings = board.gather_check_layout(tmp_path)  # must not raise

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "sys.exit" in findings[0].message


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

    findings = _run(_StubLayoutModule(), _Script())

    assert [f.status for f in findings] == [DoctorStatus.OK], (
        f"a failed page teardown was reported as a failed measurement: "
        f"{[(f.status.value, f.message) for f in findings]}"
    )
    assert "could not be measured" not in findings[0].message
    assert findings[0].evidence["measured"] == 6


def test_the_served_directory_is_the_target_not_the_layout_scripts_own_home() -> None:
    """`clm.HERE` is `check_layout.py`'s own `__file__` parent, which is a
    DIFFERENT directory than `target/docs/dashboard` whenever the file is
    symlinked or shared -- the gather then validated one repo's data.js and
    measured another's board. The original had no `target` parameter, so this
    seam is new to the port."""
    clm = _StubLayoutModule()
    served: list[Path] = []
    clm._serve = lambda here: (served.append(here), (clm.httpd, 9999))[1]
    clm.HERE = Path("/somewhere/else/entirely")

    _run(clm, _Script())

    assert served == [Path("/t") / "docs" / "dashboard"], (
        f"the gather measured a directory other than its target: {served}"
    )


def test_a_check_layout_that_exits_at_CALL_time_degrades_to_warn() -> None:
    """`SystemExit` from the dynamically-loaded file's own `check()` is a
    `BaseException`: neither the per-width `except Exception` nor
    `degrade_on_exception` saw it, so it escaped the gather.

    Doubles as the pin on `measured`'s meaning: it is incremented AFTER
    `check()` returns, so a `check()` that never completes cannot be counted
    toward the OK message's "console bar edges held, no overlap" claim.
    """
    clm = _StubLayoutModule()

    def _exit(*_a, **_k):
        raise SystemExit("boom from check()")

    clm.check = _exit

    findings = _run(clm, _Script())  # must not raise

    assert [f.status for f in findings] == [DoctorStatus.WARN], (
        f"an evaluation that never ran was reported as a clean grid: "
        f"{[(f.status.value, f.message) for f in findings]}"
    )
    assert "boom from check()" in findings[0].message


@pytest.mark.skipif(not _HAVE_REAL_DASHBOARD,
                     reason="real docs/dashboard/check_layout.py not present in this checkout")
def test_real_check_layout_exposes_the_attribute_surface_the_orchestration_uses() -> None:
    """`_run_check_layout` reads `_serve`, `WIDE`, `NARROW`, `PRESSURES`,
    `APPLY`, `PROBE` and `check` off the dynamically loaded module, but every
    test above drives it through `_StubLayoutModule`, which DEFINES those names
    rather than verifying them. A rename in the real file would make the gather
    raise `AttributeError`, degrade to WARN, and become a permanently green
    no-op with a fully green suite. This is the mirror of the sibling
    `test_real_generate_py_loads_and_exposes_the_expected_attribute_surface`.
    """
    clm = board._load_check_layout(_REPO_ROOT)

    assert callable(clm._serve)
    assert callable(clm.check)
    assert callable(clm._rows)
    assert isinstance(clm.WIDE, tuple) and clm.WIDE
    assert isinstance(clm.NARROW, tuple) and clm.NARROW
    assert isinstance(clm.PRESSURES, tuple) and clm.PRESSURES
    assert isinstance(clm.APPLY, str) and isinstance(clm.PROBE, str)
    assert isinstance(clm.DESIGN_SIZE, int)
