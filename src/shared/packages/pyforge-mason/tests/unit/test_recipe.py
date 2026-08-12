"""Story 2.4 -- `recipe.py::new`: source/package/output forwarded verbatim
to CFE's `generate_recipe` adapter, raising a typed error on CFE-root
unresolved or a non-zero CFE exit (FR-7).

`probe_import_floor`/`generate_recipe` are patched on `pyforge.mason.cfe`'s
own module namespace, not on imported names -- mirroring `test_doctor.py`'s
identical `cfe.probe_import_floor` patch target: `recipe.py` does `from .
import cfe` and calls `cfe.<name>(...)`, an attribute lookup at call time
(and `cfe.py`'s own `ensure_import_floor` calls `probe_import_floor`
unqualified, resolved via that same module's globals at call time), so
patching the attribute on the `cfe` module reaches both call sites with no
gotcha -- the same pitfall `test_cfe.py::test_ensure_cfe_root_never_re_
resolves` documents for `cfe.py` itself.

Every test below resolves the CFE root against Story 1.9's real
`fake_cfe_root` fixture (or a genuinely marker-less `tmp_path` for the
not-found case), rather than a synthetic root -- `new`'s own job is pure
composition of already-tested pieces (`resolve.py`'s chains, `cfe.py`'s
raising siblings and adapter), so these tests prove the composition, not
those pieces' own internals again."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from pyforge.mason import recipe
from pyforge.mason.cfe import ImportFloorResult
from pyforge.mason.errors import CfeUnresolvedError, RecipeGenerationError
from pyforge.mason.models import CfeResult

_EMPTY_FLOOR = ImportFloorResult(interpreter="/fake/python", missing=())
"""A satisfied import-floor result, so `ensure_import_floor` never raises
and -- since this IS the function `probe_import_floor` that would otherwise
spawn a subprocess -- never spawns one either, keeping the tests below
hermetic against whatever floor packages this test environment happens to
have installed."""


# --- I/O & Edge-Case Matrix --------------------------------------------------

@pytest.mark.parametrize("source", ["pypi", "github", "cran", "npm"])
def test_new_forwards_source_as_the_adapters_first_argv_element(source, fake_cfe_root):
    """FR-7: `source` is CFE's own subcommand vocabulary, already selected by
    `cli.py` before this function ever runs -- `new` applies no mapping of
    its own, only forwards `[source, package, "--output", output]` unmodified
    (spec Always boundary)."""
    fake_result = CfeResult(returncode=0, stdout="ok", stderr="", json_body=None)
    with patch("pyforge.mason.cfe.probe_import_floor", return_value=_EMPTY_FLOOR), \
         patch("pyforge.mason.cfe.generate_recipe", return_value=fake_result) as mock_generate:
        result = recipe.new(
            source, "demo-package", "recipes/demo",
            cfe_root_arg=str(fake_cfe_root), cfe_python_arg=None,
            cfe_timeout_arg=None, environ={}, start_directory=fake_cfe_root,
        )

    assert result == fake_result
    args = mock_generate.call_args.args[0]
    assert args == [source, "demo-package", "--output", "recipes/demo"]
    assert args[0] == source


def test_new_raises_recipe_generation_error_carrying_the_fixtures_stdout(
    fake_cfe_root, monkeypatch,
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
            recipe.new(
                "pypi", "demo", "recipes/demo",
                cfe_root_arg=str(fake_cfe_root), cfe_python_arg=sys.executable,
                cfe_timeout_arg=15.0, environ={}, start_directory=fake_cfe_root,
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
            recipe.new(
                "pypi", "demo", "recipes/demo",
                cfe_root_arg=None, cfe_python_arg=None,
                cfe_timeout_arg=None, environ={}, start_directory=tmp_path,
            )

    mock_run.assert_not_called()
