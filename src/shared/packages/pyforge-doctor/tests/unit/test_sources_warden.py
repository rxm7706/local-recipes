"""Unit tests for ``pyforge.doctor.sources.warden`` (Story 1.2) -- covers
every row of the spec's I/O & Edge-Case Matrix: all-healthy, one-engine-
missing, ``pyforge-warden`` absent, and the live equivalence check against
``pyforge.warden.engines.run_doctor_checks`` called directly -- plus the
review-hardened failure shapes: warden installed-but-unimportable (a
transitive dep's ``ModuleNotFoundError``, a non-ImportError raised by
warden's module body, and a renamed symbol's plain ``ImportError``), the
genuine-absence ``ModuleNotFoundError`` shape (naming the parent, not the
child the None-sentinel simulation produces), a malformed
``run_doctor_checks`` result, and a truthy-non-bool ``ok``.
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources.warden import gather
from pyforge.warden import engines as engines_mod
from pyforge.warden.engines import DoctorCheck


def _checks(*specs: tuple[str, bool, str]) -> tuple[DoctorCheck, ...]:
    return tuple(DoctorCheck(name=n, ok=ok, message=m) for n, ok, m in specs)


# --- all engines/feeds healthy ----------------------------------------------


def test_all_healthy_maps_six_ok_findings(monkeypatch, tmp_path: Path):
    checks = _checks(
        ("deptry", True, "within tested range"),
        ("osv-scanner", True, "within tested range"),
        ("osv-db", True, "snapshot fresh"),
        ("kev-feed", True, "operating air-gapped"),
        ("epss-feed", True, "operating air-gapped"),
        ("endoflife-feed", True, "operating air-gapped"),
    )
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: checks)

    findings = gather(tmp_path)

    assert len(findings) == 6
    for finding, check in zip(findings, checks):
        assert isinstance(finding, Finding)
        assert finding.source is Source.WARDEN_DOCTOR
        assert finding.check == check.name
        assert finding.status is DoctorStatus.OK
        assert finding.message == check.message
        assert finding.evidence == {}


# --- one engine missing -----------------------------------------------------


def test_one_engine_missing_reports_one_fail_others_ok(
    monkeypatch, tmp_path: Path
):
    checks = _checks(
        ("deptry", True, "within tested range"),
        ("osv-scanner", False, "osv-scanner binary not found on PATH"),
        ("osv-db", True, "snapshot fresh"),
        ("kev-feed", True, "operating air-gapped"),
        ("epss-feed", True, "operating air-gapped"),
        ("endoflife-feed", True, "operating air-gapped"),
    )
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: checks)

    findings = gather(tmp_path)

    assert len(findings) == 6
    statuses = {finding.check: finding.status for finding in findings}
    assert statuses["osv-scanner"] is DoctorStatus.FAIL
    assert statuses["deptry"] is DoctorStatus.OK
    assert statuses["osv-db"] is DoctorStatus.OK
    assert statuses["kev-feed"] is DoctorStatus.OK
    assert statuses["epss-feed"] is DoctorStatus.OK
    assert statuses["endoflife-feed"] is DoctorStatus.OK
    failing = next(f for f in findings if f.check == "osv-scanner")
    assert failing.message == "osv-scanner binary not found on PATH"


# --- pyforge-warden not installed -------------------------------------------


def test_pyforge_warden_absent_returns_one_fail_finding_no_exception(
    monkeypatch, tmp_path: Path
):
    # The bare parent-only patch isn't enough here: this test module (and
    # others in the suite) already imported ``pyforge.warden.engines``
    # earlier in the process, so it sits cached in sys.modules under its
    # own full dotted key -- Python's import machinery returns that cached
    # module directly without ever re-checking the parent's sys.modules
    # entry. Drop the cached submodule too so the parent-is-None sentinel
    # is actually consulted, faithfully simulating an absent install.
    monkeypatch.setitem(sys.modules, "pyforge.warden", None)
    monkeypatch.delitem(sys.modules, "pyforge.warden.engines", raising=False)

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.WARDEN_DOCTOR
    assert finding.check == "pyforge-warden"
    assert finding.status is DoctorStatus.FAIL
    assert "pip install pyforge-doctor[gate]" in finding.message


# --- warden installed but unimportable --------------------------------------


class _RaisingLoader(importlib.abc.Loader):
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise self._exc


class _RaisingEnginesFinder(importlib.abc.MetaPathFinder):
    """Meta-path hook making ``pyforge.warden.engines``'s re-import raise,
    simulating an installed-but-broken warden without touching the real
    install."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pyforge.warden.engines":
            return importlib.util.spec_from_loader(
                fullname, _RaisingLoader(self._exc)
            )
        return None


def _simulate_broken_engines_import(monkeypatch, exc: BaseException) -> None:
    monkeypatch.delitem(sys.modules, "pyforge.warden.engines", raising=False)
    monkeypatch.setattr(
        sys, "meta_path", [_RaisingEnginesFinder(exc), *sys.meta_path]
    )


def test_genuine_absence_shape_names_parent_and_gets_install_hint(
    monkeypatch, tmp_path: Path
):
    # A REAL missing dist raises ModuleNotFoundError naming the PARENT
    # ("pyforge.warden"); the None-sentinel simulation above provably
    # raises a different shape (the child, "pyforge.warden.engines", via
    # CPython's "'pyforge.warden' is not a package" branch). Cover the
    # genuine shape too, so dropping "pyforge.warden" from
    # _WARDEN_MODULES cannot survive the suite while misrouting the
    # story's headline warden-not-installed scenario (review finding,
    # 2026-07-30).
    _simulate_broken_engines_import(
        monkeypatch,
        ModuleNotFoundError(
            "No module named 'pyforge.warden'", name="pyforge.warden"
        ),
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "pyforge-warden"
    assert finding.status is DoctorStatus.FAIL
    assert "pip install pyforge-doctor[gate]" in finding.message


def test_transitive_module_not_found_reports_broken_not_absent(
    monkeypatch, tmp_path: Path
):
    # A ModuleNotFoundError naming anything OUTSIDE the pyforge.warden
    # chain means warden IS installed -- the install hint would misdirect
    # the operator (review finding, 2026-07-30).
    _simulate_broken_engines_import(
        monkeypatch,
        ModuleNotFoundError("No module named 'packaging'", name="packaging"),
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.WARDEN_DOCTOR
    assert finding.check == "pyforge-warden"
    assert finding.status is DoctorStatus.FAIL
    assert "install the `gate` extra" not in finding.message
    assert "pip install pyforge-doctor[gate]" not in finding.message
    assert "packaging" in finding.message


def test_non_import_error_during_warden_import_returns_one_fail_finding(
    monkeypatch, tmp_path: Path
):
    # A non-ImportError from warden's module body (corrupted install) must
    # degrade to a Finding, not escape gather() (review finding,
    # 2026-07-30).
    _simulate_broken_engines_import(
        monkeypatch, OSError("simulated corrupted install")
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.FAIL
    assert "pip install pyforge-doctor[gate]" not in finding.message
    assert "simulated corrupted install" in finding.message


class _EmptyModuleLoader(importlib.abc.Loader):
    """Loads an EMPTY ``pyforge.warden.engines`` -- the module imports
    fine but exports nothing, so the from-import itself raises the plain
    ``ImportError`` ("cannot import name ...") a renamed symbol
    produces."""

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        pass


class _EmptyEnginesFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "pyforge.warden.engines":
            return importlib.util.spec_from_loader(
                fullname, _EmptyModuleLoader()
            )
        return None


def test_renamed_symbol_plain_import_error_reports_broken_not_absent(
    monkeypatch, tmp_path: Path
):
    # A future warden renaming run_doctor_checks is the likeliest
    # real-world trigger of the import guard's except-Exception arm --
    # the module docstring's "renamed symbol's plain ImportError" shape,
    # previously the one documented shape with zero coverage (review
    # finding, 2026-07-30).
    monkeypatch.delitem(sys.modules, "pyforge.warden.engines", raising=False)
    monkeypatch.setattr(
        sys, "meta_path", [_EmptyEnginesFinder(), *sys.meta_path]
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "pyforge-warden"
    assert finding.status is DoctorStatus.FAIL
    assert "pip install pyforge-doctor[gate]" not in finding.message
    assert "run_doctor_checks" in finding.message


# --- run_doctor_checks raises after a successful import --------------------


def test_run_doctor_checks_raising_returns_one_fail_finding_no_exception(
    monkeypatch, tmp_path: Path
):
    def _boom(target):
        raise RuntimeError("simulated warden self-check crash")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.WARDEN_DOCTOR
    assert finding.check == "pyforge-warden"
    assert finding.status is DoctorStatus.FAIL
    # Distinct from the missing-extra message -- an installed-but-broken
    # warden must never be told to "install the gate extra".
    assert "install the `gate` extra" not in finding.message
    assert "simulated warden self-check crash" in finding.message


def test_truthy_non_bool_ok_fails_safe_as_fail(monkeypatch, tmp_path: Path):
    # A shape-drifted `ok` that is truthy but not the bool True (e.g. the
    # string "false") must map FAIL, never false-green as OK -- the
    # normalization uses strict `is True`, not truthiness (review
    # finding, 2026-07-30).
    class _DriftedCheck:
        name = "osv-db"
        ok = "false"
        message = "shape-drifted ok field"

    monkeypatch.setattr(
        engines_mod, "run_doctor_checks", lambda target: [_DriftedCheck()]
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "osv-db"
    assert finding.status is DoctorStatus.FAIL
    assert finding.message == "shape-drifted ok field"


def test_malformed_doctor_checks_return_one_fail_finding_no_exception(
    monkeypatch, tmp_path: Path
):
    # Normalization sits inside the same guard as the call itself: a
    # shape-drifted DoctorCheck (missing fields) degrades to a Finding
    # instead of raising AttributeError out of gather() (review finding,
    # 2026-07-30).
    monkeypatch.setattr(
        engines_mod, "run_doctor_checks", lambda target: [object()]
    )

    findings = gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.WARDEN_DOCTOR
    assert finding.check == "pyforge-warden"
    assert finding.status is DoctorStatus.FAIL
    assert "pip install pyforge-doctor[gate]" not in finding.message


# --- live equivalence with run_doctor_checks called directly ---------------


def test_live_equivalence_with_run_doctor_checks(tmp_path: Path):
    from pyforge.warden.engines import run_doctor_checks

    findings = gather(tmp_path)
    checks = run_doctor_checks(tmp_path)

    assert len(findings) == len(checks)
    for finding, check in zip(findings, checks):
        assert finding.check == check.name
        assert (finding.status is DoctorStatus.OK) == check.ok
        assert finding.message == check.message
