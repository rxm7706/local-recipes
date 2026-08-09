"""Story 1.8 -- `doctor.py`'s `build_report`: composes `resolve.py`'s two
pure chains, `cfe.py`'s import-floor probe, and `engines.py`'s engine probe
into one frozen `DoctorReport`, never raising.

`resolve_cfe_root`/`resolve_cfe_interpreter`/`probe_known_engines` are
patched on `doctor.py`'s own module namespace (`pyforge.mason.doctor.*`),
not on their owning modules: `doctor.py` binds each name directly via
`from .x import name` at module scope, so patching the owning module's
attribute would not reach the name `doctor.py` actually calls -- the same
gotcha `test_cfe.py::test_ensure_cfe_root_never_re_resolves` documents for
`cfe.py`. `cfe.probe_import_floor` is the one exception: `doctor.py` imports
`cfe` itself (lazily) and calls `cfe.probe_import_floor(...)`, an attribute
lookup at call time, so patching `pyforge.mason.cfe.probe_import_floor`
does reach it.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest

import pyforge.mason.doctor as doctor_module
from pyforge.mason.cfe import ImportFloorResult
from pyforge.mason.doctor import DoctorReport, build_report
from pyforge.mason.engines import EngineStatus
from pyforge.mason.resolve import (
    STEP_CWD_WALK, STEP_ENVIRONMENT, STEP_FLAG, STEP_NOT_FOUND,
    STEP_RUNNING_INTERPRETER, ResolvedCfeInterpreter, ResolvedCfeRoot,
)

_INTERPRETER = ResolvedCfeInterpreter(path="/fake/python", step=STEP_RUNNING_INTERPRETER)
_ENGINES = (
    EngineStatus(name="pixi", available=True, version="pixi 0.72.2"),
    EngineStatus(name="twine", available=False, version=None),
)


def _build(root, interpreter, missing, engines=_ENGINES):
    floor_result = ImportFloorResult(interpreter=interpreter.path, missing=missing)
    with patch.object(doctor_module, "resolve_cfe_root", return_value=root), \
         patch.object(doctor_module, "resolve_cfe_interpreter", return_value=interpreter), \
         patch("pyforge.mason.cfe.probe_import_floor", return_value=floor_result), \
         patch.object(doctor_module, "probe_known_engines", return_value=engines):
        return build_report(None, None, {}, Path("/start"))


# --- I/O & Edge-Case Matrix --------------------------------------------------

def test_root_resolved_and_floor_satisfied_reports_no_unavailable_verbs():
    root = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_CWD_WALK)
    report = _build(root, _INTERPRETER, missing=())

    assert report.cfe_root == "/fake/cfe"
    assert report.cfe_root_step == STEP_CWD_WALK
    assert report.cfe_import_floor_satisfied is True
    assert report.cfe_import_floor_missing == ()
    assert report.unavailable_verbs == ()


def test_root_unresolved_reports_none_root_and_recipe_unavailable():
    root = ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)
    report = _build(root, _INTERPRETER, missing=())

    assert report.cfe_root is None
    assert report.cfe_root_step == STEP_NOT_FOUND
    assert report.unavailable_verbs == ("recipe",)


def test_root_resolved_but_floor_missing_some_modules_reports_recipe_unavailable():
    root = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_FLAG)
    report = _build(root, _INTERPRETER, missing=("pyyaml", "requests"))

    assert report.cfe_import_floor_satisfied is False
    assert report.cfe_import_floor_missing == ("pyyaml", "requests")
    assert report.unavailable_verbs == ("recipe",)


def test_root_unresolved_and_floor_missing_still_names_recipe_exactly_once():
    root = ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)
    report = _build(root, _INTERPRETER, missing=("pyyaml",))

    assert report.unavailable_verbs == ("recipe",)


def test_report_never_lists_package_or_environment_as_unavailable():
    """AD-6: `package`/`environment` are CFE-independent and must never
    appear in `unavailable_verbs`, regardless of CFE/floor state."""
    root = ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND)
    report = _build(root, _INTERPRETER, missing=("pyyaml", "requests", "packaging"))

    assert "package" not in report.unavailable_verbs
    assert "environment" not in report.unavailable_verbs


# --- Field composition -------------------------------------------------------

def test_report_names_mason_version_and_interpreter_step():
    from pyforge.mason import __version__

    root = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_ENVIRONMENT)
    interpreter = ResolvedCfeInterpreter(path="/env/python", step=STEP_ENVIRONMENT)
    report = _build(root, interpreter, missing=())

    assert report.mason_version == __version__
    assert report.cfe_interpreter == "/env/python"
    assert report.cfe_interpreter_step == STEP_ENVIRONMENT


def test_report_carries_every_known_engine_status_through_unchanged():
    root = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_FLAG)
    report = _build(root, _INTERPRETER, missing=(), engines=_ENGINES)

    assert report.engines == _ENGINES


def test_cfe_root_is_a_plain_string_not_a_path_object():
    """`render.py::render_json` hands `dataclasses.asdict(report)` straight
    to `json.dumps`, which cannot serialize a `Path` -- `cfe_root` must
    already be converted."""
    root = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_FLAG)
    report = _build(root, _INTERPRETER, missing=())

    assert isinstance(report.cfe_root, str)


def test_doctor_report_is_frozen():
    report = _build(ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND), _INTERPRETER, missing=())

    with pytest.raises(FrozenInstanceError):
        report.mason_version = "9.9.9"  # type: ignore[misc]


# --- build_report never raises -----------------------------------------------

@pytest.mark.parametrize("step", [STEP_FLAG, STEP_ENVIRONMENT, STEP_CWD_WALK, STEP_NOT_FOUND])
@pytest.mark.parametrize("missing", [(), ("pyyaml",), tuple("abcdef")])
def test_build_report_never_raises_for_any_root_step_or_floor_gap(step, missing):
    root = ResolvedCfeRoot(root=None if step == STEP_NOT_FOUND else Path("/fake/cfe"), step=step)
    report = _build(root, _INTERPRETER, missing=missing)

    assert isinstance(report, DoctorReport)


def test_build_report_never_raises_against_a_real_unresolved_environment(tmp_path, monkeypatch):
    """End-to-end, with nothing mocked: a `tmp_path` with no CFE marker
    directory anywhere above it and an empty `environ` exercises the real
    `resolve.py` chains, the real `cfe.probe_import_floor` subprocess probe
    (against `sys.executable`, the fallback interpreter), and the real
    `engines.probe_known_engines()` PATH lookups -- proving the full,
    unmocked composition never raises (AD-16: no real CFE installation
    required).

    Review pass (2026-08-09): `probe_known_engines()` calls the real
    `shutil.which`, which reads the process's actual `PATH` environment
    variable -- passing an empty `environ` *argument* to `build_report`
    does not isolate that (it only affects the `MASON_CFE_ROOT`/
    `MASON_CFE_PYTHON` lookups `resolve.py` performs). Left unpatched, this
    test's outcome for `report.engines` depended on whatever engine
    binaries happened to be installed on the runner, violating AD-16's
    hermetic-test requirement the rest of this suite follows. Pointing the
    real `PATH` at an empty directory makes every engine probe reliably
    report absent, while `resolve.py`'s chains and `cfe.py`'s real
    subprocess probe (invoked by its full `sys.executable` path, unaffected
    by `PATH`) remain genuinely unmocked."""
    empty_path_dir = tmp_path / "empty-path"
    empty_path_dir.mkdir()
    monkeypatch.setenv("PATH", str(empty_path_dir))

    report = build_report(None, None, {}, tmp_path)

    assert isinstance(report, DoctorReport)
    assert report.cfe_root is None
    assert report.cfe_root_step == STEP_NOT_FOUND
    assert report.unavailable_verbs == ("recipe",)
    assert len(report.engines) == 4
    assert all(not status.available for status in report.engines)
