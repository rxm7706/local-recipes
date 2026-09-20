"""Story 1.9 -- the fake CFE root fixture itself: every row of the spec's
I/O & Edge-Case Matrix, run as real subprocesses (this exercises the
fixture, not a real CFE install -- consistent with AD-16)."""

from __future__ import annotations

import os
import subprocess
import sys

from pyforge.mason.resolve import STEP_CWD_WALK, ResolvedCfeRoot, resolve_cfe_root

_VALIDATE_RECIPE = "validate_recipe.py"
_SUBMIT_PR = "submit_pr.py"
_VALIDATE_RECIPE_CANNED_STDOUT = (
    '{"passed": true, "errors": [], "warnings": [], "info": [], "rattler_lint_ran": true}\n'
)
_SUBMIT_PR_CANNED_STDOUT = (
    '{"success": true, "recipe": "example-recipe", '
    '"branch": "add-example-recipe", "github_user": "example-user", '
    '"pr_url": "https://github.com/example/example/pull/1", '
    '"message": "PR created: https://github.com/example/example/pull/1"}\n'
)
_CLEAN_ENV = {key: value for key, value in os.environ.items() if not key.startswith("MASON_FIXTURE_")}
"""The ambient environment with any `MASON_FIXTURE_*` leakage stripped --
used by every "default canned output" assertion below so a stray env var set
in the runner's shell can never silently override an expected default."""


def _script_path(fake_cfe_root, name):
    return fake_cfe_root / ".claude" / "scripts" / "conda-forge-expert" / name


def _run(script_path, env=_CLEAN_ENV):
    return subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env,
    )


# --- I/O & Edge-Case Matrix ------------------------------------------------


def test_default_canned_stdout_and_exit_zero(fake_cfe_root):
    """Stub invoked with no env overrides: stdout is exactly the script's
    canned JSON body; exit code 0."""
    result = _run(_script_path(fake_cfe_root, _VALIDATE_RECIPE))
    assert result.stdout == _VALIDATE_RECIPE_CANNED_STDOUT
    assert result.returncode == 0


def test_exit_code_override_changes_exit_code(fake_cfe_root):
    """`MASON_FIXTURE_EXIT_CODE` overrides the exit code; stdout body is
    unchanged."""
    env = {**_CLEAN_ENV, "MASON_FIXTURE_EXIT_CODE": "3"}
    result = _run(_script_path(fake_cfe_root, _VALIDATE_RECIPE), env=env)
    assert result.returncode == 3
    assert result.stdout == _VALIDATE_RECIPE_CANNED_STDOUT


def test_stdout_override_changes_stdout_body(fake_cfe_root):
    """`MASON_FIXTURE_STDOUT` overrides the stdout body instead of the
    canned default."""
    env = {**_CLEAN_ENV, "MASON_FIXTURE_STDOUT": '{"x": 1}'}
    result = _run(_script_path(fake_cfe_root, _VALIDATE_RECIPE), env=env)
    assert result.stdout == '{"x": 1}\n'
    assert result.returncode == 0


def test_progress_line_prepends_a_line_before_the_json_body(fake_cfe_root):
    """`MASON_FIXTURE_PROGRESS_LINE` prepends a plain, non-JSON line before
    the (canned or overridden) JSON body -- exercises the tolerant-parsing
    path (FR-4)."""
    env = {**_CLEAN_ENV, "MASON_FIXTURE_PROGRESS_LINE": "Resolving deps..."}
    result = _run(_script_path(fake_cfe_root, _VALIDATE_RECIPE), env=env)
    lines = result.stdout.splitlines()
    assert lines == ["Resolving deps...", _VALIDATE_RECIPE_CANNED_STDOUT.rstrip("\n")]
    assert result.returncode == 0


def test_fixture_tree_resolves_as_a_cfe_root(fake_cfe_root):
    """The fixture tree resolves via `resolve_cfe_root` with
    `step=STEP_CWD_WALK` and `root=fake_cfe_root.resolve()` -- proves
    `.claude/scripts/conda-forge-expert` is a real marker directory. Compares
    against the `.resolve()`d path, mirroring `test_resolve.py`'s own
    established pattern for walk-target equality checks, so this assertion
    stays correct even where `fake_cfe_root` traverses a symlink."""
    result = resolve_cfe_root(None, {}, fake_cfe_root)
    assert result == ResolvedCfeRoot(root=fake_cfe_root.resolve(), step=STEP_CWD_WALK)


def test_second_stub_script_works_independently(fake_cfe_root):
    """`submit_pr.py`, invoked with no env set, emits its own distinct
    canned JSON body and exits 0 -- proves the mechanism generalizes past
    one script."""
    result = _run(_script_path(fake_cfe_root, _SUBMIT_PR))
    assert result.stdout == _SUBMIT_PR_CANNED_STDOUT
    assert result.returncode == 0
