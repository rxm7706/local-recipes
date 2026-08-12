"""Story 2.7 -- `recipe.py`'s `diagnose()`: composes `resolve.py`'s two pure
chains with `cfe.py`'s `ensure_cfe_root`/`diagnose_failure`, mirroring
`doctor.build_report`'s composition shape (Story 1.8) with one addition --
an unresolved root propagates as `CfeUnresolvedError` rather than folding
into report data.

`resolve_cfe_root`/`resolve_cfe_interpreter` are patched on `recipe.py`'s
own module namespace (`pyforge.mason.recipe.*`), not on their owning
`resolve.py` -- `recipe.py` binds each name directly via `from .resolve
import ...` at module scope, so patching the owning module's attribute
would not reach the name `recipe.py` actually calls (the same gotcha
`test_doctor.py`'s module docstring documents). `cfe.ensure_cfe_root`/
`cfe.diagnose_failure` are the opposite case: `recipe.py` imports `cfe`
itself and calls `cfe.ensure_cfe_root(...)`/`cfe.diagnose_failure(...)`, an
attribute lookup at call time, so patching `pyforge.mason.cfe.<name>`
directly does reach it.

Story 2.8 extends this file with `optimize()`/`scan()`: the same
composition shape as `diagnose()`, plus one addition neither `diagnose()`
nor `build` needs -- both call `cfe.ensure_import_floor(resolved_
interpreter.path)` after resolving the interpreter and before invoking
their own CFE adapter (spec Always boundary; see `recipe.py`'s module
docstring for why). Coverage mirrors `diagnose()`'s tests exactly, plus
three additions this gate is specified to have: a positive
"`ensure_import_floor` IS called" test (the inverse of Story 2.7's
`test_diagnose_never_calls_ensure_import_floor`); a REAL, unmocked
import-floor-missing propagation test against `sys.executable` (the spec's
own empirical note: the `pyforge-mason` pixi env genuinely lacks
`ruamel.yaml`/`requests`/`pyyaml`, so no mocking is needed to exercise a
real `CfeImportFloorError` raise); and a real-fixture round-trip test that
fakes ONLY the floor verdict, by patching `cfe.probe_import_floor`'s return
value rather than `subprocess.run` wholesale (spec Design Notes: a blanket
`subprocess.run` patch would also intercept `_invoke_captured`'s own real
call against the fixture stub).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import pyforge.mason.recipe as recipe_module
from pyforge.mason.cfe import ImportFloorResult
from pyforge.mason.errors import CfeImportFloorError, CfeUnresolvedError
from pyforge.mason.models import CfeResult
from pyforge.mason.recipe import diagnose, optimize, scan
from pyforge.mason.resolve import (
    STEP_CWD_WALK, STEP_NOT_FOUND, STEP_RUNNING_INTERPRETER,
    ResolvedCfeInterpreter, ResolvedCfeRoot,
)

_ROOT = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_CWD_WALK)
_INTERPRETER = ResolvedCfeInterpreter(path="/fake/python", step=STEP_RUNNING_INTERPRETER)
_RESULT = CfeResult(returncode=0, stdout="{}", stderr="", json_body={"success": True})


# --- Composition (mocked) ----------------------------------------------------

def test_diagnose_passes_log_path_as_the_sole_diagnose_failure_argument():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure, \
         patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT) as mock_diagnose:
        result = diagnose(
            "build.log",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    mock_ensure.assert_called_once_with(_ROOT)
    mock_diagnose.assert_called_once_with(
        ["build.log"], root=_ROOT.root, interpreter=_INTERPRETER.path, timeout=None,
    )
    assert result is _RESULT


def test_diagnose_passes_an_explicit_cfe_timeout_arg_straight_through():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT) as mock_diagnose:
        diagnose(
            "build.log",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=42.0,
            environ={}, start_directory=Path("/start"),
        )

    assert mock_diagnose.call_args.kwargs["timeout"] == 42.0


def test_diagnose_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `diagnose()` returns `cfe.diagnose_failure`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT):
        result = diagnose(
            "build.log",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    assert result is _RESULT
    assert isinstance(result, CfeResult)


def test_diagnose_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    """`resolve_cfe_root`/`resolve_cfe_interpreter` do their own flag ->
    environment -> default resolution -- `diagnose()` must pass the raw flag
    values through unresolved, mirroring `doctor.build_report`'s contract."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root, \
         patch.object(
             recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER,
         ) as mock_interp, \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT):
        diagnose(
            "build.log",
            cfe_root_arg="/explicit/root", cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None, environ={"X": "1"}, start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_diagnose_never_calls_ensure_import_floor():
    """Review pass: the module docstring's "no import-floor gate" decision
    (`failure_analyzer.py` is stdlib-only, confirmed by reading it) had no
    positive regression test -- a future re-addition of the gate would only
    be caught incidentally, if at all."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT), \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor:
        diagnose(
            "build.log",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    mock_ensure_floor.assert_not_called()


# --- CFE-unresolved propagation: raises before any subprocess spawns -------

def test_diagnose_raises_cfe_unresolved_error_when_root_is_not_found():
    with patch.object(
        recipe_module, "resolve_cfe_root",
        return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
    ), patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER):
        with pytest.raises(CfeUnresolvedError):
            diagnose(
                "build.log",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=Path("/start"),
            )


def test_diagnose_never_calls_diagnose_failure_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.diagnose_failure` is ever reached."""
    with patch.object(
        recipe_module, "resolve_cfe_root",
        return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
    ), patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.diagnose_failure") as mock_diagnose:
        with pytest.raises(CfeUnresolvedError):
            diagnose(
                "build.log",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=Path("/start"),
            )

    mock_diagnose.assert_not_called()


def test_diagnose_raises_before_any_subprocess_spawns_against_a_real_unresolved_root(
    tmp_path,
):
    """End-to-end, nothing mocked but the subprocess boundary itself: a
    `tmp_path` with no CFE marker directory anywhere above it and an empty
    `environ` exercises the real `resolve.py` chain and the real
    `cfe.ensure_cfe_root` raise path (AD-16: no real CFE installation
    required). `subprocess.run` is patched only to prove it is never
    called -- the spec's own wording for this row (spec I/O matrix: "raises
    ... before any subprocess spawns")."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            diagnose(
                "build.log",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Real end-to-end against fake_cfe_root (AD-16, no mocking) -------------

def test_diagnose_against_fake_cfe_root_returns_the_fixtures_canned_diagnosis(
    fake_cfe_root, monkeypatch,
):
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = diagnose(
        "build.log",
        cfe_root_arg=str(fake_cfe_root), cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0, environ={}, start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 0
    assert result.json_body["success"] is True
    assert result.json_body["error_class"] == "MODULE_NOT_FOUND_AT_TEST"


def test_diagnose_against_fake_cfe_root_with_a_real_cfe_root_walk(fake_cfe_root, monkeypatch):
    """Proves the CFE-root resolution chain itself runs for real (upward
    filesystem walk, `STEP_CWD_WALK`), not just the final subprocess call --
    `start_directory` is a subdirectory of `fake_cfe_root`, so the walk must
    ascend at least one level to find the marker, with no `--cfe-root`/
    `MASON_CFE_ROOT` given at all."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = diagnose(
        "build.log",
        cfe_root_arg=None, cfe_python_arg=sys.executable, cfe_timeout_arg=15.0,
        environ={}, start_directory=fake_cfe_root / ".claude",
    )

    assert result.returncode == 0
    assert result.json_body["success"] is True


# =============================================================================
# Story 2.8: optimize() -- mirrors diagnose()'s composition shape, plus the
# import-floor gate (spec Always boundary, module docstring).
# =============================================================================

_OPTIMIZE_RESULT = CfeResult(
    returncode=1,
    stdout='{"success": true, "suggestions_found": 1, "suggestions": []}',
    stderr="",
    json_body={"success": True, "suggestions_found": 1, "suggestions": []},
)


# --- Composition (mocked) ----------------------------------------------------

def test_optimize_passes_recipe_path_as_the_sole_optimize_recipe_argument():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure_root, \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor, \
         patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT) as mock_optimize:
        result = optimize(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    mock_ensure_root.assert_called_once_with(_ROOT)
    mock_ensure_floor.assert_called_once_with(_INTERPRETER.path)
    mock_optimize.assert_called_once_with(
        ["recipes/foo"], root=_ROOT.root, interpreter=_INTERPRETER.path, timeout=None,
    )
    assert result is _OPTIMIZE_RESULT


def test_optimize_passes_an_explicit_cfe_timeout_arg_straight_through():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor"), \
         patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT) as mock_optimize:
        optimize(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=42.0,
            environ={}, start_directory=Path("/start"),
        )

    assert mock_optimize.call_args.kwargs["timeout"] == 42.0


def test_optimize_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `optimize()` returns `cfe.optimize_recipe`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor"), \
         patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT):
        result = optimize(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    assert result is _OPTIMIZE_RESULT
    assert isinstance(result, CfeResult)


def test_optimize_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root, \
         patch.object(
             recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER,
         ) as mock_interp, \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor"), \
         patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT):
        optimize(
            "recipes/foo",
            cfe_root_arg="/explicit/root", cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None, environ={"X": "1"}, start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_optimize_calls_ensure_import_floor_with_the_resolved_interpreter():
    """Positive control -- the inverse of Story 2.7's
    `test_diagnose_never_calls_ensure_import_floor`: `optimize()` is the
    first `recipe` verb that MUST gate on CFE's import floor (module
    docstring), so this pins that it actually does, not just that it could."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor, \
         patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT):
        optimize(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    mock_ensure_floor.assert_called_once_with(_INTERPRETER.path)


# --- CFE-unresolved propagation: raises before any subprocess spawns -------

def test_optimize_raises_cfe_unresolved_error_when_root_is_not_found():
    with patch.object(
        recipe_module, "resolve_cfe_root",
        return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
    ), patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER):
        with pytest.raises(CfeUnresolvedError):
            optimize(
                "recipes/foo",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=Path("/start"),
            )


def test_optimize_never_calls_optimize_recipe_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.optimize_recipe` (and therefore `cfe.ensure_import_floor`) is ever
    reached."""
    with patch.object(
        recipe_module, "resolve_cfe_root",
        return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
    ), patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor, \
         patch("pyforge.mason.cfe.optimize_recipe") as mock_optimize:
        with pytest.raises(CfeUnresolvedError):
            optimize(
                "recipes/foo",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=Path("/start"),
            )

    mock_ensure_floor.assert_not_called()
    mock_optimize.assert_not_called()


def test_optimize_raises_before_any_subprocess_spawns_against_a_real_unresolved_root(
    tmp_path,
):
    """End-to-end, nothing mocked but the subprocess boundary itself: a
    `tmp_path` with no CFE marker directory anywhere above it and an empty
    `environ` exercises the real `resolve.py` chain and the real
    `cfe.ensure_cfe_root` raise path (AD-16: no real CFE installation
    required) -- root resolution fails before the interpreter is ever
    probed for the import floor, so `subprocess.run` is genuinely never
    called."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            optimize(
                "recipes/foo",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Import-floor-missing propagation: real, unmocked (spec Design Notes) --

def test_optimize_raises_cfe_import_floor_error_against_a_real_unresolved_floor(
    fake_cfe_root,
):
    """Empirical note (spec Design Notes): `pixi run -e pyforge-mason python
    -c "import ruamel.yaml"` fails -- the lean `pyforge-mason` pixi env
    genuinely lacks CFE's import floor. Calling `optimize()` with
    `cfe_python_arg=sys.executable` and NO floor faking therefore exercises
    a REAL, unmocked `CfeImportFloorError` raise -- no mocking of the floor
    probe itself needed. `cfe.optimize_recipe` is patched only to prove the
    gate fires before the wrapped script's own subprocess spawns."""
    with patch("pyforge.mason.cfe.optimize_recipe") as mock_optimize:
        with pytest.raises(CfeImportFloorError):
            optimize(
                "recipes/foo",
                cfe_root_arg=str(fake_cfe_root), cfe_python_arg=sys.executable,
                cfe_timeout_arg=None, environ={}, start_directory=fake_cfe_root,
            )

    mock_optimize.assert_not_called()


# --- Real end-to-end against fake_cfe_root, floor faked (AD-16, Design Notes)

def test_optimize_against_fake_cfe_root_returns_the_fixtures_canned_suggestions(
    fake_cfe_root, monkeypatch,
):
    """Design Notes: patches `cfe.probe_import_floor`'s return value, not
    `subprocess.run` wholesale -- a blanket `subprocess.run` patch would
    also intercept `_invoke_captured`'s own real call against the fixture
    stub. This fakes only the floor-satisfied verdict, leaving the actual
    invocation's subprocess call genuinely real."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        "pyforge.mason.cfe.probe_import_floor",
        lambda interpreter: ImportFloorResult(interpreter=interpreter, missing=()),
    )

    result = optimize(
        "recipes/example",
        cfe_root_arg=str(fake_cfe_root), cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0, environ={}, start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 1
    assert result.json_body["success"] is True
    assert result.json_body["suggestions_found"] == 1
    assert result.json_body["suggestions"][0]["code"] == "ABT-001"


# =============================================================================
# Story 2.8: scan() -- identical shape to optimize() above, against
# `cfe.scan_for_vulnerabilities` instead of `cfe.optimize_recipe`.
# =============================================================================

_SCAN_RESULT = CfeResult(
    returncode=0,
    stdout='{"success": true, "total_vulnerabilities": 0, "results": []}',
    stderr="",
    json_body={"success": True, "total_vulnerabilities": 0, "results": []},
)


# --- Composition (mocked) ----------------------------------------------------

def test_scan_passes_json_flag_then_recipe_path_as_scan_for_vulnerabilities_args():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure_root, \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor, \
         patch(
             "pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT,
         ) as mock_scan:
        result = scan(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    mock_ensure_root.assert_called_once_with(_ROOT)
    mock_ensure_floor.assert_called_once_with(_INTERPRETER.path)
    mock_scan.assert_called_once_with(
        ["--json", "recipes/foo"], root=_ROOT.root, interpreter=_INTERPRETER.path, timeout=None,
    )
    assert result is _SCAN_RESULT


def test_scan_passes_an_explicit_cfe_timeout_arg_straight_through():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor"), \
         patch(
             "pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT,
         ) as mock_scan:
        scan(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=42.0,
            environ={}, start_directory=Path("/start"),
        )

    assert mock_scan.call_args.kwargs["timeout"] == 42.0


def test_scan_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `scan()` returns `cfe.scan_for_vulnerabilities`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping, no
    Mason-side severity/threshold policy."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor"), \
         patch("pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT):
        result = scan(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    assert result is _SCAN_RESULT
    assert isinstance(result, CfeResult)


def test_scan_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root, \
         patch.object(
             recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER,
         ) as mock_interp, \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor"), \
         patch("pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT):
        scan(
            "recipes/foo",
            cfe_root_arg="/explicit/root", cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None, environ={"X": "1"}, start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_scan_calls_ensure_import_floor_with_the_resolved_interpreter():
    """Positive control, mirroring `optimize()`'s own -- `scan()` is the
    second `recipe` verb that MUST gate on CFE's import floor (module
    docstring)."""
    with patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT), \
         patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_cfe_root"), \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor, \
         patch("pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT):
        scan(
            "recipes/foo",
            cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
            environ={}, start_directory=Path("/start"),
        )

    mock_ensure_floor.assert_called_once_with(_INTERPRETER.path)


# --- CFE-unresolved propagation: raises before any subprocess spawns -------

def test_scan_raises_cfe_unresolved_error_when_root_is_not_found():
    with patch.object(
        recipe_module, "resolve_cfe_root",
        return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
    ), patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER):
        with pytest.raises(CfeUnresolvedError):
            scan(
                "recipes/foo",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=Path("/start"),
            )


def test_scan_never_calls_scan_for_vulnerabilities_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.scan_for_vulnerabilities` (and therefore `cfe.ensure_import_floor`)
    is ever reached."""
    with patch.object(
        recipe_module, "resolve_cfe_root",
        return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
    ), patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER), \
         patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor, \
         patch("pyforge.mason.cfe.scan_for_vulnerabilities") as mock_scan:
        with pytest.raises(CfeUnresolvedError):
            scan(
                "recipes/foo",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=Path("/start"),
            )

    mock_ensure_floor.assert_not_called()
    mock_scan.assert_not_called()


def test_scan_raises_before_any_subprocess_spawns_against_a_real_unresolved_root(
    tmp_path,
):
    """End-to-end, nothing mocked but the subprocess boundary itself --
    mirrors `optimize()`'s own version of this test."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            scan(
                "recipes/foo",
                cfe_root_arg=None, cfe_python_arg=None, cfe_timeout_arg=None,
                environ={}, start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Import-floor-missing propagation: real, unmocked (spec Design Notes) --

def test_scan_raises_cfe_import_floor_error_against_a_real_unresolved_floor(
    fake_cfe_root,
):
    """Empirical note (spec Design Notes): the lean `pyforge-mason` pixi env
    genuinely lacks `requests`/`pyyaml` too. Calling `scan()` with
    `cfe_python_arg=sys.executable` and NO floor faking therefore exercises
    a REAL, unmocked `CfeImportFloorError` raise, mirroring `optimize()`'s
    own version of this test."""
    with patch("pyforge.mason.cfe.scan_for_vulnerabilities") as mock_scan:
        with pytest.raises(CfeImportFloorError):
            scan(
                "recipes/foo",
                cfe_root_arg=str(fake_cfe_root), cfe_python_arg=sys.executable,
                cfe_timeout_arg=None, environ={}, start_directory=fake_cfe_root,
            )

    mock_scan.assert_not_called()


# --- Real end-to-end against fake_cfe_root, floor faked (AD-16, Design Notes)

def test_scan_against_fake_cfe_root_returns_the_fixtures_canned_clean_scan(
    fake_cfe_root, monkeypatch,
):
    """Mirrors `optimize()`'s own real-fixture round-trip test: patches
    `cfe.probe_import_floor`'s return value, not `subprocess.run`
    wholesale."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(
        "pyforge.mason.cfe.probe_import_floor",
        lambda interpreter: ImportFloorResult(interpreter=interpreter, missing=()),
    )

    result = scan(
        "recipes/example",
        cfe_root_arg=str(fake_cfe_root), cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0, environ={}, start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 0
    assert result.json_body["success"] is True
    assert result.json_body["total_vulnerabilities"] == 0
    assert result.json_body["results"] == []
