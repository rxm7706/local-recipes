"""Story 5.3 -- FR-46/AD-16: `recipe.py::validate`'s own docstring already
claims "no Mason-side reinterpretation" of CFE's `validate_recipe.py`
output, but nothing previously ran both paths against identical input and
diffed the results. This file adds that proof.

"Through Mason" means calling `recipe.validate()` directly (the same
function `cli.py`'s `recipe validate` dispatch calls) -- never spawning a
`mason` CLI subprocess (spec Always boundary). The "direct" side builds its
own `subprocess.run` call against `<root>/.claude/scripts/conda-forge-
expert/validate_recipe.py` independently, rather than importing `cfe.py`'s
private `_CFE_SCRIPTS`/`_invoke_captured` (AD-3 reserves those names to
`cfe.py` alone) -- reusing Mason's own path-construction would hide exactly
the kind of drift this test exists to catch.

Real-root discovery goes through `_find_real_cfe_root`, a thin wrapper over
`resolve.py::resolve_cfe_root(None, {}, start_directory)` -- an EMPTY
environ, never `os.environ` (spec Always boundary; see this story's own
Spec Change Log: an ambient `MASON_CFE_ROOT` pointing at a bad path must
never intercept this resolution, or the "skip cleanly when CFE is absent"
guarantee (AC3) becomes unsound and the helper's own unit test becomes
non-hermetic). `_find_real_cfe_root`'s fast unit test below proves the
no-marker-upward case returns `None` in isolation, without needing an
actual "CFE absent" environment for the slow test itself.

Unlike every other file in this suite (AD-16: fixture CFE root, no real
subprocess dependency), the `@pytest.mark.slow` test below needs a REAL
CFE installation on disk -- present when this suite runs inside this very
repository (`pixi run -e pyforge-mason pyforge-mason-test-slow`), absent in
an extracted/standalone checkout, in which case it skips rather than fails
(AC3). Mirrors `test_package_build.py`'s module-docstring/derivation style
for this suite's other "needs a real external dependency, `slow`-marked"
test.

The fixture recipe (`tests/fixtures/delegation_fidelity_recipe/recipe.yaml`)
is real and parseable but deliberately NOT lint-clean -- the comparison is
Mason vs. direct CFE output, not "the recipe is valid," and a recipe
producing some errors/warnings is a *more* convincing fidelity proof than a
trivial `passed: true`-on-both-sides case, since it exercises list
equality rather than just a bool.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pyforge.mason import recipe
from pyforge.mason.resolve import resolve_cfe_root

_FIXTURE_RECIPE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "delegation_fidelity_recipe" / "recipe.yaml"
)

_DIRECT_INVOKE_TIMEOUT_SECONDS = 120.0
"""Mirrors `cfe.py`'s own `_VALIDATE_RECIPE_TIMEOUT_SECONDS` -- the direct
side is a hand-built `subprocess.run` call, not `cfe.validate_recipe`
itself, so it pins its own matching timeout rather than importing that
private constant (AD-3)."""


def _find_real_cfe_root(start_directory: Path) -> Path | None:
    """Resolve a REAL CFE root upward from `start_directory`, or `None` if
    none resolves (spec Always boundary).

    A thin wrapper over `resolve_cfe_root(None, {}, start_directory)` --
    `explicit=None` and an EMPTY `environ` so only the upward filesystem
    walk (`STEP_CWD_WALK`) can match; never `os.environ`, whose ambient
    `MASON_CFE_ROOT` could otherwise point at a nonexistent path and break
    both this function's own hermeticity and the slow test's "skip cleanly
    when CFE is absent" guarantee (AC3; see this story's Spec Change Log).
    """
    return resolve_cfe_root(None, {}, start_directory).root


def test_find_real_cfe_root_returns_none_with_no_cfe_marker_upward(tmp_path):
    """Proves AC3's skip condition in isolation: a `tmp_path` has no
    `.claude/scripts/conda-forge-expert` marker anywhere in its ancestry,
    so the upward walk exhausts and `_find_real_cfe_root` returns `None` --
    hermetically, with no dependency on the runner's own shell environment
    (an empty `environ` is passed through regardless of what the actual
    process environment holds)."""
    assert _find_real_cfe_root(tmp_path) is None


def test_delegation_fidelity_test_skips_when_no_real_cfe_root_resolves(monkeypatch):
    """AC3, exercised at the actual call site: the helper-level unit test
    above only proves `_find_real_cfe_root` itself returns `None` -- it
    never runs the `if root is None: pytest.skip(...)` line inside
    `test_delegation_fidelity_mason_matches_direct_cfe_invocation`, which
    always finds a real root in this repository and so never takes that
    branch under normal collection (review finding, Blind Hunter). Forcing
    `_find_real_cfe_root` to return `None` and calling the slow test
    function directly proves the branch itself skips rather than fails,
    without needing an actual CFE-absent environment."""
    monkeypatch.setattr(f"{__name__}._find_real_cfe_root", lambda start_directory: None)
    with pytest.raises(pytest.skip.Exception):
        test_delegation_fidelity_mason_matches_direct_cfe_invocation()


@pytest.mark.slow
def test_delegation_fidelity_mason_matches_direct_cfe_invocation():
    """AC1: run the fixture recipe through `recipe.validate()` (Mason) and,
    separately, through a raw subprocess invoking `validate_recipe.py
    --json` directly -- both against the same real, resolved CFE root and
    the same fixture -- and assert `returncode`/parsed-JSON-body match
    exactly. Skips (AC3) when no real CFE root resolves upward from this
    test file's own location, rather than failing.
    """
    root = _find_real_cfe_root(Path(__file__).resolve().parent)
    if root is None:
        pytest.skip("no real CFE root resolved upward from this test file's location")

    mason_result = recipe.validate(
        str(_FIXTURE_RECIPE_PATH),
        cfe_root_arg=str(root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=None,
        environ={},
        start_directory=root,
    )

    script_path = root / ".claude" / "scripts" / "conda-forge-expert" / "validate_recipe.py"
    direct = subprocess.run(
        [sys.executable, str(script_path), "--json", str(_FIXTURE_RECIPE_PATH)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=_DIRECT_INVOKE_TIMEOUT_SECONDS,
        check=False,
    )

    assert mason_result.returncode == direct.returncode
    assert mason_result.json_body == json.loads(direct.stdout)
    # Guards against a future conda-forge-expert lint-rule relaxation
    # silently making the fixture lint-clean, which would degrade this test
    # to the trivial "passed: true on both sides" case its own docstring
    # says it deliberately avoids, with no signal that the degradation
    # happened (spec Design Notes).
    errors = mason_result.json_body["errors"]
    assert errors
    # A bare truthiness check above would also pass if the resolved
    # `cfe_python_arg`/`sys.executable` lacked PyYAML: validate_recipe_yaml
    # returns the single-item list ["PyYAML not installed - cannot
    # validate"] in that case, which is truthy but proves nothing about
    # fidelity -- both sides would trivially "agree" on the same
    # short-circuit message instead of exercising the fixture's real
    # content (review finding, Blind Hunter). Reject that degenerate case
    # explicitly so a missing PyYAML silently collapsing this test's proof
    # is itself a failure, not a silent pass.
    assert errors != ["PyYAML not installed - cannot validate"]
