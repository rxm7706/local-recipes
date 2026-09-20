"""Story 2.4 -- `recipe.py::new()`: the first `recipe` verb's use-case
module. `source`/`package`/`output` are forwarded verbatim to CFE's
`generate_recipe` adapter, raising a typed error on CFE-root unresolved or
a non-zero CFE exit (FR-7).

`probe_import_floor`/`generate_recipe` are patched on `pyforge.mason.cfe`'s
own module namespace, not on imported names -- mirroring `test_doctor.py`'s
identical `cfe.probe_import_floor` patch target: `recipe.py` does `from .
import cfe` and calls `cfe.<name>(...)`, an attribute lookup at call time
(and `cfe.py`'s own `ensure_import_floor` calls `probe_import_floor`
unqualified, resolved via that same module's globals at call time), so
patching the attribute on the `cfe` module reaches both call sites with no
gotcha -- the same pitfall `test_cfe.py::test_ensure_cfe_root_never_re_
resolves` documents for `cfe.py` itself. Every `new()` test resolves the
CFE root against Story 1.9's real `fake_cfe_root` fixture (or a genuinely
marker-less `tmp_path` for the not-found case), rather than a synthetic
root -- `new`'s own job is pure composition of already-tested pieces
(`resolve.py`'s chains, `cfe.py`'s raising siblings and adapter), so these
tests prove the composition, not those pieces' own internals again.

Story 2.5 -- `recipe.py::validate()`: the second `recipe` verb's use-case
module, hand-landed 2026-08-13 after this story's own dev pass deferred on
a spec-surface gate, not a code defect (see `recipe.py`'s own module
docstring and this Spec's memlog for the same reconciliation applied
there). Mirrors `diagnose()`'s composition-test shape below exactly (argv/
timeout passthrough, verbatim-return, `ensure_import_floor` never called,
`CfeUnresolvedError` propagation), plus two real-fixture round trips
against `fake_cfe_root`: a passing canned result (the fixture's own
default) and a failing one produced via the `MASON_FIXTURE_STDOUT`/
`MASON_FIXTURE_EXIT_CODE` override mechanism (Story 1.9), since the
fixture's `validate_recipe.py` stub only emits a canned passing body on its
own.

Story 2.6 -- `recipe.py::build()`: the next `recipe` verb's use-case
module. Resolves the CFE root and raises `CfeUnresolvedError` before any
subprocess spawns when it cannot be found; otherwise dispatches to `cfe.
build_native` (default) or `cfe.build_docker` (`docker=True`) -- proven
against Story 1.9's `fake_cfe_root` fixture, real subprocess, no mocking
(mirrors this suite's established fixture-round-trip style for a
CFE-dependent use-case, e.g. this file's own `validate_recipe`/`submit_pr`-
style coverage below).

Story 2.7 -- `recipe.py`'s `diagnose()`: composes `resolve.py`'s two pure
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
nor `build` needs -- both call `cfe.probe_import_floor(resolved_
interpreter.path)` themselves after resolving the interpreter and raise
`CfeImportFloorError` before invoking their own CFE adapter, but ONLY when
their own operation-relevant subset of `.missing` is non-empty -- never the
whole 6-entry floor (`cfe.ensure_import_floor` is called by neither; spec
Always boundary; see `recipe.py`'s module docstring for why). Coverage
mirrors `diagnose()`'s tests exactly, plus several additions this scoped
gate is specified to have: a positive "`probe_import_floor` IS called" test
(the inverse of Story 2.7's `test_diagnose_never_calls_ensure_import_floor`);
a test that an interpreter missing only an operation-UNRELATED floor entry
is NOT rejected; a test that the call IS rejected when its own single
relevant floor entry (`ruamel.yaml` for `optimize()`; `pyyaml` or `requests`
for `scan()`) is missing, originally exercised as a REAL, unmocked probe
against `sys.executable` (the spec's own empirical note: the `pyforge-mason`
pixi env genuinely lacked `ruamel.yaml`/`requests`/`pyyaml`, so no mocking
was needed) but converted to a mock of `probe_import_floor`'s return value
by Story 3.1, whose own required change (`twine`/`conda-lock` landing as
`pyforge-mason` conda run-dependencies) permanently pulls all three into
that SAME shared pixi environment -- see `test_optimize_is_rejected_when_
the_relevant_floor_entry_is_missing`'s docstring for the full account; and
a real-fixture round-trip test that fakes ONLY the floor verdict, by
patching `cfe.probe_import_floor`'s return value rather than `subprocess.
run` wholesale (spec Design Notes: a blanket `subprocess.run` patch would
also intercept `_invoke_captured`'s own real call against the fixture
stub).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import pyforge.mason.recipe as recipe_module
from pyforge.mason.cfe import ImportFloorResult
from pyforge.mason.engines.build_hooks import RattlerBuildPlugin
from pyforge.mason.errors import CfeImportFloorError, CfeUnresolvedError, RecipeGenerationError
from pyforge.mason.models import BuildResult, CfeResult, ShipState, ShipTargetResult
from pyforge.mason.recipe import build, diagnose, new, optimize, scan, submit, update, validate
from pyforge.mason.resolve import (
    STEP_CWD_WALK,
    STEP_NOT_FOUND,
    STEP_RUNNING_INTERPRETER,
    ResolvedCfeInterpreter,
    ResolvedCfeRoot,
)

_ROOT = ResolvedCfeRoot(root=Path("/fake/cfe"), step=STEP_CWD_WALK)
_INTERPRETER = ResolvedCfeInterpreter(path="/fake/python", step=STEP_RUNNING_INTERPRETER)
_RESULT = CfeResult(returncode=0, stdout="{}", stderr="", json_body={"success": True})

_FIXTURE_ENV_VARS = ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE")


def _clear_fixture_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _FIXTURE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


_EMPTY_FLOOR = ImportFloorResult(interpreter="/fake/python", missing=())
"""A satisfied import-floor result, so `ensure_import_floor` never raises
and -- since this IS the function `probe_import_floor` that would otherwise
spawn a subprocess -- never spawns one either, keeping the tests below
hermetic against whatever floor packages this test environment happens to
have installed."""


# --- new(): I/O & Edge-Case Matrix --------------------------------------------


@pytest.mark.parametrize("source", ["pypi", "github", "cran", "npm"])
def test_new_forwards_source_as_the_adapters_first_argv_element(source, fake_cfe_root):
    """FR-7: `source` is CFE's own subcommand vocabulary, already selected by
    `cli.py` before this function ever runs -- `new` applies no mapping of
    its own, only forwards `[source, package, "--output", output]` unmodified
    (spec Always boundary)."""
    fake_result = CfeResult(returncode=0, stdout="ok", stderr="", json_body=None)
    with (
        patch("pyforge.mason.cfe.probe_import_floor", return_value=_EMPTY_FLOOR),
        patch("pyforge.mason.cfe.generate_recipe", return_value=fake_result) as mock_generate,
    ):
        result = new(
            source,
            "demo-package",
            "recipes/demo",
            cfe_root_arg=str(fake_cfe_root),
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=fake_cfe_root,
        )

    assert result == fake_result
    args = mock_generate.call_args.args[0]
    assert args == [source, "demo-package", "--output", "recipes/demo"]
    assert args[0] == source


def test_new_raises_recipe_generation_error_carrying_the_fixtures_stdout(
    fake_cfe_root,
    monkeypatch,
):
    """`MASON_FIXTURE_EXIT_CODE=1` against the real fixture stub, real
    subprocess, no mocking of `generate_recipe` itself -- proves
    `RecipeGenerationError` carries CFE's own stdout verbatim (the fixture's
    canned body), not a Mason-invented message (spec I/O matrix)."""
    monkeypatch.delenv("MASON_FIXTURE_STDOUT", raising=False)
    monkeypatch.delenv("MASON_FIXTURE_PROGRESS_LINE", raising=False)
    monkeypatch.setenv("MASON_FIXTURE_EXIT_CODE", "1")

    with patch("pyforge.mason.cfe.probe_import_floor", return_value=_EMPTY_FLOOR):
        with pytest.raises(RecipeGenerationError) as excinfo:
            new(
                "pypi",
                "demo",
                "recipes/demo",
                cfe_root_arg=str(fake_cfe_root),
                cfe_python_arg=sys.executable,
                cfe_timeout_arg=15.0,
                environ={},
                start_directory=fake_cfe_root,
            )

    assert excinfo.value.source == "pypi"
    assert "Generated: recipes/demo/recipe.yaml" in excinfo.value.cfe_message


def test_new_raises_cfe_unresolved_error_before_any_subprocess_spawns(tmp_path):
    """A not-found root (a genuinely marker-less, isolated `tmp_path` --
    `test_resolve.py::test_walk_exhausts_to_filesystem_root`'s identical
    setup) must be caught before `ensure_import_floor`'s probe or
    `generate_recipe` itself ever spawns a process (spec I/O matrix): every
    subprocess spawn in this package funnels through `cfe.py`'s own
    `subprocess.run` call, so asserting it was never invoked proves no
    process launched at all, not merely that this test's happy-path
    assertions were skipped."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            new(
                "pypi",
                "demo",
                "recipes/demo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- build(): I/O & Edge-Case Matrix ------------------------------------------


def test_build_native_happy_path_against_fake_cfe_root(fake_cfe_root, monkeypatch):
    _clear_fixture_env(monkeypatch)
    monkeypatch.setattr("pyforge.mason.cfe.detect_native_build_config", lambda: "linux64")

    result = build(
        "recipes/foo",
        docker=False,
        config=None,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=None,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert isinstance(result, BuildResult)
    assert result.mode == "native"
    assert result.config == "linux64"
    assert result.artifact_dir == "build_artifacts/linux64"
    assert result.returncode == 0


def test_build_native_stamps_rattler_build_via_the_default_hook(
    fake_cfe_root,
    monkeypatch,
):
    """Native ``build()`` selects the default plugin and runs ``around``;
    context ``engine`` is rattler-build and ``next`` is today's native
    backend (no extra subprocess beyond the fixture)."""
    _clear_fixture_env(monkeypatch)
    monkeypatch.setattr("pyforge.mason.cfe.detect_native_build_config", lambda: "linux64")
    engines: list[str] = []
    real_call = RattlerBuildPlugin.call

    def _spy(self, point, context):
        assert point == "around"
        assert callable(context.get("next"))
        result = real_call(self, point, context)
        engines.append(context.get("engine"))
        return result

    monkeypatch.setattr(RattlerBuildPlugin, "call", _spy)

    result = build(
        "recipes/foo",
        docker=False,
        config=None,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=None,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert isinstance(result, BuildResult)
    assert result.returncode == 0
    assert engines == ["rattler-build"]


def test_build_docker_happy_path_against_fake_cfe_root(fake_cfe_root, monkeypatch):
    _clear_fixture_env(monkeypatch)

    result = build(
        "recipes/foo",
        docker=True,
        config="linux64",
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert isinstance(result, BuildResult)
    assert result.mode == "docker"
    assert result.config == "linux64"
    assert result.artifact_dir == "build_artifacts/linux64"
    assert result.returncode == 0


def test_build_propagates_cfe_unresolved_error_before_any_subprocess_spawns(tmp_path):
    """No `.claude/scripts/conda-forge-expert/` marker anywhere under
    `tmp_path` -- `ensure_cfe_root` must raise before either adapter is ever
    reached."""
    with pytest.raises(CfeUnresolvedError):
        build(
            "recipes/foo",
            docker=False,
            config=None,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=tmp_path,
        )


def test_build_docker_propagates_cfe_unresolved_error_too(tmp_path):
    with pytest.raises(CfeUnresolvedError):
        build(
            "recipes/foo",
            docker=True,
            config="linux64",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=tmp_path,
        )


def test_build_native_never_resolves_a_cfe_interpreter(fake_cfe_root, monkeypatch):
    """spec Always boundary: the native path invokes its script through
    `bash`, never a resolved CFE interpreter -- resolving one for this path
    would be dead work."""
    _clear_fixture_env(monkeypatch)
    monkeypatch.setattr("pyforge.mason.cfe.detect_native_build_config", lambda: None)

    def _boom(*args, **kwargs):
        raise AssertionError("resolve_cfe_interpreter must not be called for the native path")

    monkeypatch.setattr("pyforge.mason.recipe.resolve_cfe_interpreter", _boom)

    result = build(
        "recipes/foo",
        docker=False,
        config=None,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=None,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert result.mode == "native"


def test_build_docker_resolves_a_cfe_interpreter_from_the_flag(fake_cfe_root, monkeypatch):
    """`cfe_python_arg` reaches `cfe.build_docker`'s `interpreter=` --
    proven by pointing it at a nonexistent interpreter and observing the
    resulting `OSError` propagate, rather than the fixture's real
    `sys.executable` silently being used instead."""
    _clear_fixture_env(monkeypatch)

    with pytest.raises(OSError):
        build(
            "recipes/foo",
            docker=True,
            config="linux64",
            cfe_root_arg=str(fake_cfe_root),
            cfe_python_arg="/definitely/not/a/real/interpreter",
            cfe_timeout_arg=15.0,
            environ={},
            start_directory=Path("/does/not/matter"),
        )


# =============================================================================
# Story 2.5: validate() -- numerically the first `recipe` verb (see module
# docstring); mirrors diagnose()'s composition shape exactly, except `args`
# forces `--json` ahead of `recipe_path`, mirroring scan()'s own forcing.
# =============================================================================

_VALIDATE_RESULT = CfeResult(
    returncode=0,
    stdout='{"passed": true, "errors": [], "warnings": [], "info": [], "rattler_lint_ran": true}',
    stderr="",
    json_body={
        "passed": True,
        "errors": [],
        "warnings": [],
        "info": [],
        "rattler_lint_ran": True,
    },
)


# --- Composition (mocked) ----------------------------------------------------


def test_validate_passes_json_flag_then_recipe_path_as_validate_recipe_args():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure,
        patch(
            "pyforge.mason.cfe.validate_recipe",
            return_value=_VALIDATE_RESULT,
        ) as mock_validate,
    ):
        result = validate(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure.assert_called_once_with(_ROOT)
    mock_validate.assert_called_once_with(
        ["--json", "recipes/foo"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    assert result is _VALIDATE_RESULT


def test_validate_passes_an_explicit_cfe_timeout_arg_straight_through():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.validate_recipe",
            return_value=_VALIDATE_RESULT,
        ) as mock_validate,
    ):
        validate(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=42.0,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_validate.call_args.kwargs["timeout"] == 42.0


def test_validate_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `validate()` returns `cfe.validate_recipe`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping, no
    Mason-side pass/fail reinterpretation (that projection is `cli.py`'s own
    dispatch-time decision, not this function's)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.validate_recipe", return_value=_VALIDATE_RESULT),
    ):
        result = validate(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result is _VALIDATE_RESULT
    assert isinstance(result, CfeResult)


def test_validate_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root,
        patch.object(
            recipe_module,
            "resolve_cfe_interpreter",
            return_value=_INTERPRETER,
        ) as mock_interp,
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.validate_recipe", return_value=_VALIDATE_RESULT),
    ):
        validate(
            "recipes/foo",
            cfe_root_arg="/explicit/root",
            cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None,
            environ={"X": "1"},
            start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_validate_never_calls_ensure_import_floor():
    """spec Always boundary: the wrapped validator's only third-party
    import, PyYAML, already degrades to an honest failure on its own -- no
    import-floor gate, mirroring `diagnose()`'s own established exemption,
    not `optimize()`/`scan()`'s scoped-probe pattern."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.validate_recipe", return_value=_VALIDATE_RESULT),
        patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor,
        patch("pyforge.mason.cfe.probe_import_floor") as mock_probe_floor,
    ):
        validate(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure_floor.assert_not_called()
    mock_probe_floor.assert_not_called()


# --- CFE-unresolved propagation: raises before any subprocess spawns -------


def test_validate_raises_cfe_unresolved_error_when_root_is_not_found():
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
    ):
        with pytest.raises(CfeUnresolvedError):
            validate(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )


def test_validate_never_calls_validate_recipe_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.validate_recipe` is ever reached."""
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.validate_recipe") as mock_validate,
    ):
        with pytest.raises(CfeUnresolvedError):
            validate(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    mock_validate.assert_not_called()


def test_validate_raises_before_any_subprocess_spawns_against_a_real_unresolved_root(
    tmp_path,
):
    """End-to-end, nothing mocked but the subprocess boundary itself --
    mirrors `diagnose()`'s own version of this test."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            validate(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Real end-to-end against fake_cfe_root (AD-16, no mocking) -------------


def test_validate_against_fake_cfe_root_returns_the_fixtures_canned_passing_result(
    fake_cfe_root,
    monkeypatch,
):
    _clear_fixture_env(monkeypatch)

    result = validate(
        "recipes/example",
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 0
    assert result.json_body["passed"] is True
    assert result.json_body["errors"] == []


def test_validate_against_fake_cfe_root_returns_a_failing_result_via_fixture_override(
    fake_cfe_root,
    monkeypatch,
):
    """The fixture's own `validate_recipe.py` stub only emits a canned
    passing body (Story 1.9) -- a failing round trip needs the
    `MASON_FIXTURE_STDOUT`/`MASON_FIXTURE_EXIT_CODE` override mechanism
    already used throughout this suite (spec: 'use the... override
    mechanism... rather than editing the fixture file itself')."""
    _clear_fixture_env(monkeypatch)
    monkeypatch.setenv(
        "MASON_FIXTURE_STDOUT",
        '{"passed": false, "errors": ["missing license"], "warnings": [], "info": [], "rattler_lint_ran": true}',
    )
    monkeypatch.setenv("MASON_FIXTURE_EXIT_CODE", "1")

    result = validate(
        "recipes/example",
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 1
    assert result.json_body["passed"] is False
    assert result.json_body["errors"] == ["missing license"]


# =============================================================================
# Story 2.7: diagnose() -- mirrors doctor.build_report's composition shape.
# =============================================================================

# --- Composition (mocked) ----------------------------------------------------


def test_diagnose_passes_log_path_as_the_sole_diagnose_failure_argument():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure,
        patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT) as mock_diagnose,
    ):
        result = diagnose(
            "build.log",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure.assert_called_once_with(_ROOT)
    mock_diagnose.assert_called_once_with(
        ["build.log"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    assert result is _RESULT


def test_diagnose_passes_an_explicit_cfe_timeout_arg_straight_through():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT) as mock_diagnose,
    ):
        diagnose(
            "build.log",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=42.0,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_diagnose.call_args.kwargs["timeout"] == 42.0


def test_diagnose_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `diagnose()` returns `cfe.diagnose_failure`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT),
    ):
        result = diagnose(
            "build.log",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result is _RESULT
    assert isinstance(result, CfeResult)


def test_diagnose_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    """`resolve_cfe_root`/`resolve_cfe_interpreter` do their own flag ->
    environment -> default resolution -- `diagnose()` must pass the raw flag
    values through unresolved, mirroring `doctor.build_report`'s contract."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root,
        patch.object(
            recipe_module,
            "resolve_cfe_interpreter",
            return_value=_INTERPRETER,
        ) as mock_interp,
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT),
    ):
        diagnose(
            "build.log",
            cfe_root_arg="/explicit/root",
            cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None,
            environ={"X": "1"},
            start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_diagnose_never_calls_ensure_import_floor():
    """Review pass: the module docstring's "no import-floor gate" decision
    (`failure_analyzer.py` is stdlib-only, confirmed by reading it) had no
    positive regression test -- a future re-addition of the gate would only
    be caught incidentally, if at all."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.diagnose_failure", return_value=_RESULT),
        patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor,
    ):
        diagnose(
            "build.log",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure_floor.assert_not_called()


# --- CFE-unresolved propagation: raises before any subprocess spawns -------


def test_diagnose_raises_cfe_unresolved_error_when_root_is_not_found():
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
    ):
        with pytest.raises(CfeUnresolvedError):
            diagnose(
                "build.log",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )


def test_diagnose_never_calls_diagnose_failure_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.diagnose_failure` is ever reached."""
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.diagnose_failure") as mock_diagnose,
    ):
        with pytest.raises(CfeUnresolvedError):
            diagnose(
                "build.log",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
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
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Real end-to-end against fake_cfe_root (AD-16, no mocking) -------------


def test_diagnose_against_fake_cfe_root_returns_the_fixtures_canned_diagnosis(
    fake_cfe_root,
    monkeypatch,
):
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = diagnose(
        "build.log",
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
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
        cfe_root_arg=None,
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root / ".claude",
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
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure_root,
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ) as mock_probe_floor,
        patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT) as mock_optimize,
    ):
        result = optimize(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure_root.assert_called_once_with(_ROOT)
    mock_probe_floor.assert_called_once_with(_INTERPRETER.path)
    mock_optimize.assert_called_once_with(
        ["recipes/foo"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    assert result is _OPTIMIZE_RESULT


def test_optimize_passes_an_explicit_cfe_timeout_arg_straight_through():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ),
        patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT) as mock_optimize,
    ):
        optimize(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=42.0,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_optimize.call_args.kwargs["timeout"] == 42.0


def test_optimize_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `optimize()` returns `cfe.optimize_recipe`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ),
        patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT),
    ):
        result = optimize(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result is _OPTIMIZE_RESULT
    assert isinstance(result, CfeResult)


def test_optimize_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root,
        patch.object(
            recipe_module,
            "resolve_cfe_interpreter",
            return_value=_INTERPRETER,
        ) as mock_interp,
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ),
        patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT),
    ):
        optimize(
            "recipes/foo",
            cfe_root_arg="/explicit/root",
            cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None,
            environ={"X": "1"},
            start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_optimize_calls_probe_import_floor_with_the_resolved_interpreter():
    """Positive control -- the inverse of Story 2.7's
    `test_diagnose_never_calls_ensure_import_floor`: `optimize()` is the
    first `recipe` verb that MUST probe CFE's import floor (module
    docstring), so this pins that it actually does, not just that it could."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ) as mock_probe_floor,
        patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT),
    ):
        optimize(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_probe_floor.assert_called_once_with(_INTERPRETER.path)


def test_optimize_is_not_rejected_when_only_an_unrelated_floor_entry_is_missing():
    """Spec acceptance criterion: an interpreter missing only a floor entry
    UNRELATED to `optimize()` (everything except `ruamel.yaml`) must NOT be
    rejected -- `cfe.optimize_recipe` is still called and no
    `CfeImportFloorError` is raised."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(
                interpreter=_INTERPRETER.path,
                missing=("packaging", "truststore", "conda-forge-metadata"),
            ),
        ),
        patch("pyforge.mason.cfe.optimize_recipe", return_value=_OPTIMIZE_RESULT) as mock_optimize,
    ):
        result = optimize(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_optimize.assert_called_once()
    assert result is _OPTIMIZE_RESULT


# --- CFE-unresolved propagation: raises before any subprocess spawns -------


def test_optimize_raises_cfe_unresolved_error_when_root_is_not_found():
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
    ):
        with pytest.raises(CfeUnresolvedError):
            optimize(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )


def test_optimize_never_calls_optimize_recipe_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.optimize_recipe` (and therefore `cfe.probe_import_floor`) is ever
    reached."""
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.probe_import_floor") as mock_probe_floor,
        patch("pyforge.mason.cfe.optimize_recipe") as mock_optimize,
    ):
        with pytest.raises(CfeUnresolvedError):
            optimize(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    mock_probe_floor.assert_not_called()
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
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Import-floor-missing propagation: rejected on the relevant floor gap --


def test_optimize_is_rejected_when_the_relevant_floor_entry_is_missing():
    """`_OPTIMIZE_RELEVANT_FLOOR` is exactly `("ruamel.yaml",)` -- mocks
    `probe_import_floor` to report only that one entry missing (the other
    five floor entries present) and asserts the call is rejected on it
    alone, mirroring `scan()`'s own `test_scan_is_rejected_when_only_one_
    relevant_floor_entry_is_missing`.

    Story 3.1 note: this test was originally a REAL, unmocked probe against
    `sys.executable` (the spec's own empirical note: the lean `pyforge-mason`
    pixi env genuinely lacked `ruamel.yaml`, so no mocking was needed to
    exercise a real `CfeImportFloorError` raise -- self-diagnosed by
    asserting the precondition directly rather than assumed). That
    precondition is now permanently gone: `conda-lock` (whose own dependency
    tree includes `ruamel.yaml`) is a `pyforge-mason` conda run-dependency
    as of this same story, so `sys.executable` -- the SAME shared pixi
    environment this suite runs under -- can never again observe
    `ruamel.yaml` as missing. Mocking is the only way left to exercise this
    specific raise (see `test_scan_is_rejected_when_only_one_relevant_
    floor_entry_is_missing`'s docstring for `scan()`'s parallel, already-
    mocked coverage of the same class of gap)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(
                interpreter=_INTERPRETER.path,
                missing=("ruamel.yaml",),
            ),
        ),
        patch("pyforge.mason.cfe.optimize_recipe") as mock_optimize,
    ):
        with pytest.raises(CfeImportFloorError) as exc_info:
            optimize(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    assert exc_info.value.missing == ("ruamel.yaml",)
    mock_optimize.assert_not_called()


# --- Real end-to-end against fake_cfe_root, floor faked (AD-16, Design Notes)


def test_optimize_against_fake_cfe_root_returns_the_fixtures_canned_suggestions(
    fake_cfe_root,
    monkeypatch,
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
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
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
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure_root,
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ) as mock_probe_floor,
        patch(
            "pyforge.mason.cfe.scan_for_vulnerabilities",
            return_value=_SCAN_RESULT,
        ) as mock_scan,
    ):
        result = scan(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure_root.assert_called_once_with(_ROOT)
    mock_probe_floor.assert_called_once_with(_INTERPRETER.path)
    mock_scan.assert_called_once_with(
        ["--json", "recipes/foo"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    assert result is _SCAN_RESULT


def test_scan_passes_an_explicit_cfe_timeout_arg_straight_through():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ),
        patch(
            "pyforge.mason.cfe.scan_for_vulnerabilities",
            return_value=_SCAN_RESULT,
        ) as mock_scan,
    ):
        scan(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=42.0,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_scan.call_args.kwargs["timeout"] == 42.0


def test_scan_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `scan()` returns `cfe.scan_for_vulnerabilities`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping, no
    Mason-side severity/threshold policy."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ),
        patch("pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT),
    ):
        result = scan(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result is _SCAN_RESULT
    assert isinstance(result, CfeResult)


def test_scan_forwards_cfe_root_and_cfe_python_flag_values_unresolved():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT) as mock_root,
        patch.object(
            recipe_module,
            "resolve_cfe_interpreter",
            return_value=_INTERPRETER,
        ) as mock_interp,
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ),
        patch("pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT),
    ):
        scan(
            "recipes/foo",
            cfe_root_arg="/explicit/root",
            cfe_python_arg="/explicit/python",
            cfe_timeout_arg=None,
            environ={"X": "1"},
            start_directory=Path("/start"),
        )

    mock_root.assert_called_once_with("/explicit/root", {"X": "1"}, Path("/start"))
    mock_interp.assert_called_once_with("/explicit/python", {"X": "1"})


def test_scan_calls_probe_import_floor_with_the_resolved_interpreter():
    """Positive control, mirroring `optimize()`'s own -- `scan()` is the
    second `recipe` verb that MUST probe CFE's import floor (module
    docstring)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(interpreter=_INTERPRETER.path, missing=()),
        ) as mock_probe_floor,
        patch("pyforge.mason.cfe.scan_for_vulnerabilities", return_value=_SCAN_RESULT),
    ):
        scan(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_probe_floor.assert_called_once_with(_INTERPRETER.path)


def test_scan_is_not_rejected_when_only_an_unrelated_floor_entry_is_missing():
    """Spec acceptance criterion: an interpreter missing only a floor entry
    UNRELATED to `scan()` (everything except `requests`/`pyyaml`) must NOT be
    rejected -- `cfe.scan_for_vulnerabilities` is still called and no
    `CfeImportFloorError` is raised."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(
                interpreter=_INTERPRETER.path,
                missing=("packaging", "truststore", "ruamel.yaml", "conda-forge-metadata"),
            ),
        ),
        patch(
            "pyforge.mason.cfe.scan_for_vulnerabilities",
            return_value=_SCAN_RESULT,
        ) as mock_scan,
    ):
        result = scan(
            "recipes/foo",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_scan.assert_called_once()
    assert result is _SCAN_RESULT


@pytest.mark.parametrize("missing_package", ["pyyaml", "requests"])
def test_scan_is_rejected_when_only_one_relevant_floor_entry_is_missing(missing_package):
    """`_SCAN_RELEVANT_FLOOR` gates on EITHER `pyyaml` OR `requests` being
    missing, not both at once -- the two coverage tests around this one
    (`..._is_not_rejected_when_only_an_unrelated...` above,
    `..._against_a_real_unresolved_floor` below) each exercise an
    all-relevant-missing or no-relevant-missing extreme; neither pins the
    OR-semantics in between. Mocks `probe_import_floor` to report exactly
    one relevant package missing (the other three floor entries present) and
    asserts the call is still rejected on that single entry alone."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.probe_import_floor",
            return_value=ImportFloorResult(
                interpreter=_INTERPRETER.path,
                missing=(missing_package,),
            ),
        ),
        patch("pyforge.mason.cfe.scan_for_vulnerabilities") as mock_scan,
    ):
        with pytest.raises(CfeImportFloorError) as exc_info:
            scan(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    assert exc_info.value.missing == (missing_package,)
    mock_scan.assert_not_called()


# --- CFE-unresolved propagation: raises before any subprocess spawns -------


def test_scan_raises_cfe_unresolved_error_when_root_is_not_found():
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
    ):
        with pytest.raises(CfeUnresolvedError):
            scan(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )


def test_scan_never_calls_scan_for_vulnerabilities_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before
    `cfe.scan_for_vulnerabilities` (and therefore `cfe.probe_import_floor`)
    is ever reached."""
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.probe_import_floor") as mock_probe_floor,
        patch("pyforge.mason.cfe.scan_for_vulnerabilities") as mock_scan,
    ):
        with pytest.raises(CfeUnresolvedError):
            scan(
                "recipes/foo",
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    mock_probe_floor.assert_not_called()
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
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# Story 3.1 note: this section formerly carried a REAL, unmocked
# `sys.executable`-probe counterpart to `test_scan_is_rejected_when_only_
# one_relevant_floor_entry_is_missing` above (the spec's own empirical note:
# the lean `pyforge-mason` pixi env genuinely lacked `requests`/`pyyaml`).
# That precondition is now permanently gone: `twine` (`requests`) and
# `conda-lock` (`pyyaml`/`ruamel.yaml`) are `pyforge-mason` conda
# run-dependencies as of this same story, pulling both into `sys.executable`
# -- the SAME shared pixi environment this suite runs under -- for good.
# Removed rather than converted to a second mock of the same shape: the
# parametrized test above already covers "rejected when `pyyaml` OR
# `requests` alone is missing" with no loss of coverage (`optimize()`'s
# parallel case, above, had no other mocked coverage of its single-entry
# `ruamel.yaml` gap and was converted in place instead).


# --- Real end-to-end against fake_cfe_root, floor faked (AD-16, Design Notes)


def test_scan_against_fake_cfe_root_returns_the_fixtures_canned_clean_scan(
    fake_cfe_root,
    monkeypatch,
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
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 0
    assert result.json_body["success"] is True
    assert result.json_body["total_vulnerabilities"] == 0
    assert result.json_body["results"] == []


# =============================================================================
# Story 2.9: submit() -- resolve root/interpreter like diagnose() (no
# import-floor gate), plus the two additions unique to this verb: `recipe_
# path` IS interpreted (into a slug + CFE_RECIPES_ROOT), and the returned
# CfeResult is reinterpreted into a ShipTargetResult (module docstring,
# spec Always boundary).
# =============================================================================

_SUBMIT_DRY_RUN_RESULT = CfeResult(
    returncode=0,
    stdout=(
        '{"success": true, "dry_run": true, "recipe": "foo", '
        '"branch": "add-recipe-foo", "github_user": "example-user", '
        '"fork_branch_url": '
        '"https://github.com/example-user/staged-recipes/tree/add-recipe-foo", '
        '"message": "Dry run OK -- would push branch \'add-recipe-foo\' to '
        'example-user/staged-recipes."}'
    ),
    stderr="",
    json_body={
        "success": True,
        "dry_run": True,
        "recipe": "foo",
        "branch": "add-recipe-foo",
        "github_user": "example-user",
        "fork_branch_url": ("https://github.com/example-user/staged-recipes/tree/add-recipe-foo"),
        "message": ("Dry run OK -- would push branch 'add-recipe-foo' to example-user/staged-recipes."),
    },
)

_SUBMIT_FULL_SUCCESS_RESULT = CfeResult(
    returncode=0,
    stdout="{...}",
    stderr="",
    json_body={
        "success": True,
        "recipe": "foo",
        "branch": "add-recipe-foo",
        "github_user": "example-user",
        "pr_url": "https://github.com/conda-forge/staged-recipes/pull/123",
        "message": "PR created: https://github.com/conda-forge/staged-recipes/pull/123",
    },
)

_SUBMIT_PREPARE_ONLY_RESULT = CfeResult(
    returncode=0,
    stdout="{...}",
    stderr="",
    json_body={
        "success": True,
        "recipe": "foo",
        "branch": "add-recipe-foo",
        "github_user": "example-user",
        "fork_branch_url": ("https://github.com/example-user/staged-recipes/tree/add-recipe-foo"),
        "head_sha": "abc123",
        "synced_commits": 0,
        "pushed": True,
        "force": True,
        "message": (
            "Branch 'add-recipe-foo' is ready on example-user/staged-recipes "
            "(pushed=True, fork-was-behind=0 commits). Inspect: "
            "https://github.com/example-user/staged-recipes/tree/add-recipe-foo"
        ),
    },
)

_SUBMIT_PUSH_SUCCEEDED_PR_FAILED_RESULT = CfeResult(
    returncode=1,
    stdout="{...}",
    stderr="",
    json_body={
        "success": False,
        "error": "PR creation failed: some gh error",
        "branch": "add-recipe-foo",
        "fork_branch_url": ("https://github.com/example-user/staged-recipes/tree/add-recipe-foo"),
        "hint": "Run open_pr separately to retry the PR step.",
    },
)


# --- I/O matrix: the five state-mapping branches (mocked cfe.submit_pr) ----


def test_submit_dry_run_appends_dry_run_flag_and_returns_not_attempted():
    """Dry run (default): no `--yes` -> `confirm=False` -> `--dry-run`
    forwarded; `ShipTargetResult(state=NOT_ATTEMPTED, reference=None)` even
    though the stub's own JSON carries a `fork_branch_url` -- a dry run's
    branch URL is hypothetical and never rendered as if real (spec Always
    boundary)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure,
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_DRY_RUN_RESULT,
        ) as mock_submit_pr,
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=False,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure.assert_called_once_with(_ROOT)
    args, kwargs = mock_submit_pr.call_args
    assert args[0] == ["foo", "--dry-run"]
    assert kwargs["root"] == _ROOT.root
    assert kwargs["interpreter"] == _INTERPRETER.path
    assert kwargs["timeout"] is None
    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.NOT_ATTEMPTED,
        reference=None,
        message=_SUBMIT_DRY_RUN_RESULT.json_body["message"],
    )


def test_submit_confirmed_full_flow_returns_pending_with_pr_url():
    """Confirmed, full flow: `--yes` -> `confirm=True` -> no `--dry-run`;
    CFE reports `pr_url` -> `ShipTargetResult(state=PENDING,
    reference=pr_url)` -- never `TERMINAL` (AD-9/AD-10)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_FULL_SUCCESS_RESULT,
        ) as mock_submit_pr,
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=True,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_submit_pr.call_args.args[0] == ["foo"]
    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/conda-forge/staged-recipes/pull/123",
        message=_SUBMIT_FULL_SUCCESS_RESULT.json_body["message"],
    )


def test_submit_confirmed_prepare_only_appends_the_flag_and_returns_pending_with_branch_url():
    """Confirmed, prepare-only: `--yes --prepare-only` -> both `confirm=
    True` (no `--dry-run`) and `--prepare-only` forwarded; no `pr_url` in
    the body -> `ShipTargetResult(state=PENDING, reference=fork_branch_url)`
    (AD-10: "if a target cannot be interrogated, the result is pending with
    the reason")."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_PREPARE_ONLY_RESULT,
        ) as mock_submit_pr,
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=True,
            prepare_only=True,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_submit_pr.call_args.args[0] == ["foo", "--prepare-only"]
    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference=("https://github.com/example-user/staged-recipes/tree/add-recipe-foo"),
        message=_SUBMIT_PREPARE_ONLY_RESULT.json_body["message"],
    )


def test_submit_confirmed_push_succeeded_pr_failed_returns_failed_with_branch_url():
    """Confirmed, push succeeds but PR creation fails: CFE JSON `success=
    false` with `fork_branch_url` present (the push happened; only `open_pr`
    failed afterward) -> `ShipTargetResult(state=FAILED,
    reference=fork_branch_url)` -- data, not raised (AD-4)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_PUSH_SUCCEEDED_PR_FAILED_RESULT,
        ),
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=True,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.FAILED,
        reference=("https://github.com/example-user/staged-recipes/tree/add-recipe-foo"),
        message=_SUBMIT_PUSH_SUCCEEDED_PR_FAILED_RESULT.json_body["error"],
    )


def test_submit_computes_cfe_recipes_root_from_the_recipe_paths_parent_for_an_out_of_tree_path():
    """Out-of-tree recipe (S-2.4): `CFE_RECIPES_ROOT` is set to the recipe
    path's parent directory in the child's environment, regardless of
    whether that parent happens to be the real `recipes/` root -- no
    branching (spec Always boundary). Asserted on the `env=` argv reaching
    the mocked `cfe.submit_pr` call, mirroring `run_streamed`'s own
    documented contract that the caller builds the whole dict."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_DRY_RUN_RESULT,
        ) as mock_submit_pr,
    ):
        submit(
            "/tmp/out-of-tree-gen/my-package",
            confirm=False,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={"PATH": "/usr/bin"},
            start_directory=Path("/start"),
        )

    env = mock_submit_pr.call_args.kwargs["env"]
    assert env["CFE_RECIPES_ROOT"] == "/tmp/out-of-tree-gen"
    # The caller-supplied environ is passed through in full, plus the one
    # added key -- no credential is read, filtered, or added (AD-14).
    assert env["PATH"] == "/usr/bin"
    assert mock_submit_pr.call_args.args[0][0] == "my-package"


def test_submit_overrides_a_pre_existing_cfe_recipes_root_in_environ():
    """Review pass (2026-08-12): the prior out-of-tree test's `environ` never
    already carried a `CFE_RECIPES_ROOT` key, so it never proved OVERRIDE --
    only ADDITION. `{**environ, KEY: value}` always lets the later key win
    (Python dict-literal semantics), but a stale/wrong value already present
    in the real inherited `environ` (e.g. leaked from a parent shell) must
    still be replaced by the one `submit()` computes from `recipe_path`'s own
    parent, never merged or left alone."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_DRY_RUN_RESULT,
        ) as mock_submit_pr,
    ):
        submit(
            "/tmp/out-of-tree-gen/my-package",
            confirm=False,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={"CFE_RECIPES_ROOT": "/totally/wrong/stale/root", "PATH": "/usr/bin"},
            start_directory=Path("/start"),
        )

    env = mock_submit_pr.call_args.kwargs["env"]
    assert env["CFE_RECIPES_ROOT"] == "/tmp/out-of-tree-gen"
    assert env["PATH"] == "/usr/bin"


def test_submit_dry_run_prepare_only_composes_both_flags():
    """`--prepare-only` composes with the dry-run default (module docstring:
    "composing with --dry-run exactly as the wrapped script's own argparse
    already allows") -- confirm=False, prepare_only=True must forward BOTH
    `--dry-run` and `--prepare-only`, not just one. Every other
    `--prepare-only` test in this file pairs it with `confirm=True`; this
    pins the confirm=False pairing specifically (review pass, 2026-08-12)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=_SUBMIT_DRY_RUN_RESULT,
        ) as mock_submit_pr,
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=False,
            prepare_only=True,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_submit_pr.call_args.args[0] == ["foo", "--dry-run", "--prepare-only"]
    assert result.state == ShipState.NOT_ATTEMPTED


@pytest.mark.parametrize("returncode,expected_state", [(0, ShipState.PENDING), (1, ShipState.FAILED)])
def test_submit_confirmed_unparseable_body_falls_back_to_returncode(returncode, expected_state):
    """Review pass (2026-08-12): `_ship_target_result_from_cfe_result`'s own
    docstring calls out the unparseable/non-dict `json_body` fallback
    (`result.returncode == 0` standing in for "success") by name, but no
    prior test constructed one -- every fixture above carries a populated
    dict body. Pins both outcomes of that fallback: `returncode == 0` ->
    PENDING (an edge case CFE's real script cannot produce today -- it
    always prints its JSON body before exiting 0 -- but the fallback exists
    and must not crash), `returncode != 0` -> FAILED. Both leave `reference`
    and `message` as `None` -- there is no body to read either from."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=CfeResult(
                returncode=returncode,
                stdout="not json",
                stderr="",
                json_body=None,
            ),
        ),
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=True,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result == ShipTargetResult(
        target="conda-forge",
        state=expected_state,
        reference=None,
        message=None,
    )


def test_submit_treats_a_missing_success_key_as_failure():
    """Review pass (2026-08-12): a `dict` body that simply omits `"success"`
    entirely (as opposed to setting it explicitly `false`) must still be
    treated as failure -- `dict.get("success")` returns `None` (falsy) for
    an absent key, the same fail-closed outcome as an explicit `false`, but
    no prior test constructed a body with the key missing altogether."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=CfeResult(
                returncode=1,
                stdout="{...}",
                stderr="",
                json_body={"error": "some unexpected shape"},
            ),
        ),
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=True,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result.state == ShipState.FAILED
    assert result.message == "some unexpected shape"


def test_submit_preserves_an_explicit_empty_string_message_instead_of_falling_back_to_error():
    """Review pass (2026-08-12): the state-mapping helper used to compute
    `message` via `body.get("message") or body.get("error")` -- an `or`
    chain that silently discards a PRESENT-but-falsy `"message"` (e.g. an
    explicit empty string) in favor of `"error"`. `dict.get(key, default)`
    only substitutes `default` when `key` is absent, so a present empty
    string now survives as `""`, not `"error"`'s text."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.submit_pr",
            return_value=CfeResult(
                returncode=1,
                stdout="{...}",
                stderr="",
                json_body={"success": False, "message": "", "error": "should not win"},
            ),
        ),
    ):
        result = submit(
            "/fake/cfe/recipes/foo",
            confirm=True,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result.message == ""


def test_submit_recovers_from_an_unresolvable_recipe_path_as_a_failed_result():
    """Review pass (2026-08-12): `Path.resolve()` can raise `OSError` (e.g. a
    symlink loop) or `ValueError` (e.g. an embedded NUL byte) for a
    genuinely malformed path -- distinct from a merely NONEXISTENT one,
    which resolves cleanly and surfaces as CFE's own "Recipe not found"
    data. `submit()` must catch that and return a `FAILED` `ShipTargetResult`
    itself (AD-4: an anticipated failure is data, never a raised exception)
    rather than let a raw `OSError`/`ValueError` escape to `cli.py`'s
    generic `except Exception` handler. No subprocess may spawn afterward."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch.object(
            recipe_module.Path,
            "resolve",
            side_effect=OSError("symlink loop detected"),
        ),
        patch("pyforge.mason.cfe.submit_pr") as mock_submit_pr,
    ):
        result = submit(
            "/fake/cfe/recipes/loopy",
            confirm=True,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_submit_pr.assert_not_called()
    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.FAILED,
        reference=None,
        message="symlink loop detected",
    )


def test_submit_never_calls_probe_import_floor():
    """Mirrors `test_diagnose_never_calls_ensure_import_floor`: `submit_pr.py`
    is stdlib-only (confirmed by reading it), the same exemption
    `diagnose()` established -- `submit()` has no scoped-probe gate either
    (module docstring; unlike `optimize()`/`scan()`)."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.submit_pr", return_value=_SUBMIT_DRY_RUN_RESULT),
        patch("pyforge.mason.cfe.probe_import_floor") as mock_probe_floor,
        patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor,
    ):
        submit(
            "/fake/cfe/recipes/foo",
            confirm=False,
            prepare_only=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_probe_floor.assert_not_called()
    mock_ensure_floor.assert_not_called()


# --- CFE-unresolved propagation: raises before any subprocess spawns -------


def test_submit_raises_cfe_unresolved_error_when_root_is_not_found():
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
    ):
        with pytest.raises(CfeUnresolvedError):
            submit(
                "/fake/cfe/recipes/foo",
                confirm=False,
                prepare_only=False,
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )


def test_submit_never_calls_submit_pr_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before `cfe.
    submit_pr` is ever reached."""
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.submit_pr") as mock_submit_pr,
    ):
        with pytest.raises(CfeUnresolvedError):
            submit(
                "/fake/cfe/recipes/foo",
                confirm=False,
                prepare_only=False,
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    mock_submit_pr.assert_not_called()


def test_submit_raises_before_any_subprocess_spawns_against_a_real_unresolved_root(
    tmp_path,
):
    """End-to-end, nothing mocked but the subprocess boundary itself --
    mirrors `diagnose()`'s own version of this test (AD-16: no real CFE
    installation required)."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            submit(
                "/fake/cfe/recipes/foo",
                confirm=False,
                prepare_only=False,
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Real end-to-end against fake_cfe_root (AD-16, no mocking) -------------


def test_submit_against_fake_cfe_root_returns_the_fixtures_canned_success(
    fake_cfe_root,
    monkeypatch,
):
    """`confirm=True, prepare_only=False` -- the stub's static canned JSON
    already includes `pr_url`, matching the full-flow-success shape exactly
    (spec Code Map), so no fixture changes are needed."""
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = submit(
        str(fake_cfe_root / "recipes" / "example-recipe"),
        confirm=True,
        prepare_only=False,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
    )

    assert result == ShipTargetResult(
        target="conda-forge",
        state=ShipState.PENDING,
        reference="https://github.com/example/example/pull/1",
        message="PR created: https://github.com/example/example/pull/1",
    )


# =============================================================================
# Story 2.10: update() -- mirrors diagnose()'s composition shape exactly
# (resolve root -> ensure_cfe_root -> resolve interpreter, no import-floor
# gate); dispatches between cfe.update_recipe and cfe.update_recipe_from_
# github based on the Mason-only `github` flag, and returns the raw
# CfeResult -- no ShipTargetResult, unlike submit() (module docstring, spec
# Never boundary).
# =============================================================================

_UPDATE_RESULT = CfeResult(
    returncode=0,
    stdout='{"success": true, "updated": true, "new_version": "9.9.9"}',
    stderr="",
    json_body={"success": True, "updated": True, "new_version": "9.9.9"},
)


def test_update_default_apply_calls_update_recipe_with_recipe_path_only():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root") as mock_ensure,
        patch("pyforge.mason.cfe.update_recipe", return_value=_UPDATE_RESULT) as mock_update,
        patch("pyforge.mason.cfe.update_recipe_from_github") as mock_update_gh,
    ):
        result = update(
            "recipes/foo",
            dry_run=False,
            github=False,
            github_repo=None,
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure.assert_called_once_with(_ROOT)
    mock_update.assert_called_once_with(
        ["recipes/foo"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    mock_update_gh.assert_not_called()
    assert result is _UPDATE_RESULT


def test_update_dry_run_appends_the_dry_run_flag():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.update_recipe", return_value=_UPDATE_RESULT) as mock_update,
    ):
        update(
            "recipes/foo",
            dry_run=True,
            github=False,
            github_repo=None,
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_update.assert_called_once_with(
        ["recipes/foo", "--dry-run"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )


def test_update_github_flag_dispatches_to_update_recipe_from_github():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.update_recipe") as mock_update,
        patch(
            "pyforge.mason.cfe.update_recipe_from_github",
            return_value=_UPDATE_RESULT,
        ) as mock_update_gh,
    ):
        result = update(
            "recipes/foo",
            dry_run=True,
            github=True,
            github_repo=None,
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_update.assert_not_called()
    mock_update_gh.assert_called_once_with(
        ["recipes/foo", "--dry-run"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    assert result is _UPDATE_RESULT


def test_update_github_repo_and_pre_are_forwarded_only_with_github():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.update_recipe_from_github",
            return_value=_UPDATE_RESULT,
        ) as mock_update_gh,
    ):
        update(
            "recipes/foo",
            dry_run=False,
            github=True,
            github_repo="owner/repo",
            allow_prerelease=True,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_update_gh.assert_called_once_with(
        ["recipes/foo", "--repo", "owner/repo", "--pre"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )


def test_update_github_repo_falsy_is_not_forwarded():
    """`github_repo=""` (falsy but not `None`) must not append a bare
    `--repo` with no value -- mirrors the spec's "if truthy" wording."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch(
            "pyforge.mason.cfe.update_recipe_from_github",
            return_value=_UPDATE_RESULT,
        ) as mock_update_gh,
    ):
        update(
            "recipes/foo",
            dry_run=False,
            github=True,
            github_repo="",
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_update_gh.assert_called_once_with(
        ["recipes/foo"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )


def test_update_repo_and_pre_are_inert_without_github():
    """`--repo`/`--pre` given without `--github` never reach CFE argv at all
    (spec I/O matrix: "inert, not rejected") -- `update_recipe` (PyPI) is
    still called."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.update_recipe", return_value=_UPDATE_RESULT) as mock_update,
        patch("pyforge.mason.cfe.update_recipe_from_github") as mock_update_gh,
    ):
        result = update(
            "recipes/foo",
            dry_run=False,
            github=False,
            github_repo="owner/repo",
            allow_prerelease=True,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_update.assert_called_once_with(
        ["recipes/foo"],
        root=_ROOT.root,
        interpreter=_INTERPRETER.path,
        timeout=None,
    )
    mock_update_gh.assert_not_called()
    assert result is _UPDATE_RESULT


def test_update_passes_an_explicit_cfe_timeout_arg_straight_through():
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.update_recipe", return_value=_UPDATE_RESULT) as mock_update,
    ):
        update(
            "recipes/foo",
            dry_run=False,
            github=False,
            github_repo=None,
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=42.0,
            environ={},
            start_directory=Path("/start"),
        )

    assert mock_update.call_args.kwargs["timeout"] == 42.0


def test_update_returns_the_cfe_result_verbatim_no_reinterpretation():
    """Spec Never boundary: `update()` returns `cfe.update_recipe`'s
    `CfeResult` directly -- no new model, no field renaming, no wrapping,
    unlike `submit()`'s `ShipTargetResult`."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.update_recipe", return_value=_UPDATE_RESULT),
    ):
        result = update(
            "recipes/foo",
            dry_run=False,
            github=False,
            github_repo=None,
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    assert result is _UPDATE_RESULT
    assert isinstance(result, CfeResult)


def test_update_never_calls_ensure_import_floor():
    """Mirrors `test_diagnose_never_calls_ensure_import_floor`: both wrapped
    autotick scripts already degrade a missing dependency to JSON error data
    on their own (module docstring), so `update()` gates on neither the
    whole floor nor a scoped subset."""
    with (
        patch.object(recipe_module, "resolve_cfe_root", return_value=_ROOT),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.ensure_cfe_root"),
        patch("pyforge.mason.cfe.update_recipe", return_value=_UPDATE_RESULT),
        patch("pyforge.mason.cfe.ensure_import_floor") as mock_ensure_floor,
        patch("pyforge.mason.cfe.probe_import_floor") as mock_probe_floor,
    ):
        update(
            "recipes/foo",
            dry_run=False,
            github=False,
            github_repo=None,
            allow_prerelease=False,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=Path("/start"),
        )

    mock_ensure_floor.assert_not_called()
    mock_probe_floor.assert_not_called()


# --- CFE-unresolved propagation: raises before any subprocess spawns -------


def test_update_raises_cfe_unresolved_error_when_root_is_not_found():
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
    ):
        with pytest.raises(CfeUnresolvedError):
            update(
                "recipes/foo",
                dry_run=False,
                github=False,
                github_repo=None,
                allow_prerelease=False,
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )


def test_update_never_calls_either_adapter_when_root_is_unresolved():
    """The `CfeUnresolvedError` path must short-circuit before either
    `cfe.update_recipe`/`cfe.update_recipe_from_github` is ever reached --
    checked with `github=True` so both adapters are proven unreachable."""
    with (
        patch.object(
            recipe_module,
            "resolve_cfe_root",
            return_value=ResolvedCfeRoot(root=None, step=STEP_NOT_FOUND),
        ),
        patch.object(recipe_module, "resolve_cfe_interpreter", return_value=_INTERPRETER),
        patch("pyforge.mason.cfe.update_recipe") as mock_update,
        patch("pyforge.mason.cfe.update_recipe_from_github") as mock_update_gh,
    ):
        with pytest.raises(CfeUnresolvedError):
            update(
                "recipes/foo",
                dry_run=False,
                github=True,
                github_repo=None,
                allow_prerelease=False,
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=Path("/start"),
            )

    mock_update.assert_not_called()
    mock_update_gh.assert_not_called()


def test_update_raises_before_any_subprocess_spawns_against_a_real_unresolved_root(
    tmp_path,
):
    """End-to-end, nothing mocked but the subprocess boundary itself --
    mirrors `diagnose()`'s own version of this test (AD-16: no real CFE
    installation required)."""
    with patch("pyforge.mason.cfe.subprocess.run") as mock_run:
        with pytest.raises(CfeUnresolvedError):
            update(
                "recipes/foo",
                dry_run=False,
                github=False,
                github_repo=None,
                allow_prerelease=False,
                cfe_root_arg=None,
                cfe_python_arg=None,
                cfe_timeout_arg=None,
                environ={},
                start_directory=tmp_path,
            )

    mock_run.assert_not_called()


# --- Real end-to-end against fake_cfe_root (AD-16, no mocking) -------------


def test_update_against_fake_cfe_root_returns_the_fixtures_canned_json(
    fake_cfe_root,
    monkeypatch,
):
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = update(
        "recipes/example",
        dry_run=False,
        github=False,
        github_repo=None,
        allow_prerelease=False,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 0
    assert result.json_body["success"] is True
    assert result.json_body["new_version"] == "9.9.9"


def test_update_github_against_fake_cfe_root_returns_the_fixtures_canned_json(
    fake_cfe_root,
    monkeypatch,
):
    for var in ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE"):
        monkeypatch.delenv(var, raising=False)

    result = update(
        "recipes/example",
        dry_run=True,
        github=True,
        github_repo="owner/repo",
        allow_prerelease=True,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=fake_cfe_root,
    )

    assert isinstance(result, CfeResult)
    assert result.returncode == 0
    assert result.json_body["success"] is True
    assert result.json_body["latest_tag"] == "v9.9.9"
