"""Story 5.1 -- FR-44/FR-5: Mason's central `mason package`/`mason
environment` guarantee is that every verb there runs with no
conda-forge-expert (CFE) installation present, with exactly ONE named
exception -- the `conda-forge` ship target, which fails specifically with
`CfeUnresolvedError` (`"cfe:unresolved"`, D-2/NFR-14) rather than crashing
some other way. Nothing before this file drove the FULL non-`recipe` verb
surface end to end with the CFE root guaranteed unresolvable and checked
that guarantee held.

Behavioral, not AST-based -- unlike this directory's sibling
`test_capability_tiers.py`, which proves AD-6's "no module-level `cfe`
import" invariant by parsing `package.py`/`environment.py` as source text.
That guard proves the SHAPE of the code is right; it cannot prove that
`package.build()`, `package.ship()`, `environment.lock()`, and
`environment.check()` actually still RUN to a normal result with a real
(unresolvable) CFE-root resolution chain behind them. This file drives each
one through its real call chain -- `resolve.py::resolve_cfe_root`'s pure
walk included, unmocked -- with only the engine layer (`pep517`, `pixi`,
`twine`, `engines.condalock`) mocked (AD-16, NFR-5: offline-safe, proves
CFE-independence rather than network/tooling availability).

CFE is forced unresolvable the same way `test_package.py::test_ship_conda_
forge_raises_cfe_unresolved_when_root_is_not_found` and `test_recipe.py`'s
own `tmp_path`-based not-found cases already do: no `cfe_root_arg`, an
`environ` mapping carrying no `MASON_CFE_ROOT` key, and a `start_directory`
(pytest's own isolated `tmp_path`, under the system temp root -- nowhere
near this repository's own `.claude/scripts/conda-forge-expert/` marker)
with no CFE marker directory anywhere upward. `cfe_unresolvable` below
self-verifies that premise by calling the real `resolve_cfe_root` once and
asserting it lands in `STEP_NOT_FOUND` -- never `conftest.py`'s
`fake_cfe_root` fixture, which supplies a PRESENT root, the opposite of
what every test here needs.

`package.build()`, `environment.lock()`, and `environment.check()` all
carry no CFE parameter at all (Code Map). `build()`'s own coverage below
additionally patches `resolve_cfe_root` (where `package.py` actually binds
it) and asserts it is never called -- proof that no hidden path in `build()`
reaches for it, beyond what `test_capability_tiers.py`'s static "no
module-level `cfe` import" guard already establishes. `environment.py`
never imports `resolve_cfe_root` at all, so `lock()`/`check()` have nothing
of that shape to patch -- their coverage rests on running for real inside
the shared `cfe_unresolvable` fixture's guaranteed-unresolvable state, not
on a `resolve_cfe_root` call-count assertion. Only `package.ship()` (via
`ship_conda_forge`) takes CFE-related parameters, and only its
`conda-forge` target is allowed to depend on them --
`_CFE_DEPENDENT_SHIP_TARGETS` below is that one-entry allow-list, expressed
as a named constant the ship test iterates against (spec Always boundary):
widening it, or replacing it with a conditional, requires editing this
file's own logic, not a config flip. `pypi-test` is not separately
exercised in that ship test -- it runs through the identical `ship_pypi()`
call as `pypi`, with no CFE-related branch of its own, so `pypi`'s coverage
already speaks for it.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.mason import environment, package
from pyforge.mason.engines.condalock import CondaLockCheckResult, CondaLockResult
from pyforge.mason.engines.pep517 import Pep517BuildResult
from pyforge.mason.engines.pixi import PixiBuildResult, PixiUploadResult
from pyforge.mason.engines.twine import TwineUploadResult
from pyforge.mason.errors import CfeUnresolvedError
from pyforge.mason.models import CheckResult, LockResult, PackageBuildResult, ShipState
from pyforge.mason.resolve import STEP_NOT_FOUND, resolve_cfe_root

# --- The one-entry allow-list (spec Always/Never boundaries) ---------------

_CFE_DEPENDENT_SHIP_TARGETS = frozenset({"conda-forge"})
"""The ONLY `mason package ship` target permitted to depend on CFE (FR-44/
FR-5). Every other verb in the `package`/`environment` surface -- including
every OTHER ship target -- must run normally with the CFE root guaranteed
unresolvable. A second entry, or reshaping this into an "except where CFE
is needed" conditional, is forbidden by the spec's own Never boundary;
`test_ship_multi_target_...` below iterates against this constant rather
than hardcoding `"conda-forge"` a second time, so widening it is the one
change that would also require updating that test's own expectations."""


def test_cfe_dependent_ship_targets_allow_list_has_exactly_one_entry():
    """Structural guard, not just a comment (spec AC2): the allow-list must
    stay a one-entry `"conda-forge"` collection."""
    assert _CFE_DEPENDENT_SHIP_TARGETS == frozenset({"conda-forge"})
    assert len(_CFE_DEPENDENT_SHIP_TARGETS) == 1


# --- Shared CFE-unresolvable setup ------------------------------------------


@pytest.fixture
def cfe_unresolvable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, str], Path]:
    """Build a genuinely CFE-unresolvable `(environ, start_directory)` pair
    from `tmp_path` -- the shared setup every scenario below reuses, rather
    than duplicating "how" five times.

    `monkeypatch.delenv`/`chdir` are defense-in-depth only (AD-5: Mason
    never reads `os.environ` or `Path.cwd()` directly for CFE resolution --
    every chain takes an explicit `environ`/`start_directory` parameter) --
    the real guarantee is the self-check below: calling the actual
    `resolve_cfe_root` once, unmocked, and asserting it lands in
    `STEP_NOT_FOUND`. If that assertion ever fired, every other test in this
    file would be proving nothing (a false CFE-independence guarantee is
    worse than an untested one), so this fails loudly and immediately
    rather than letting the rest of the suite pass on a false premise.
    """
    monkeypatch.delenv("MASON_CFE_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    environ: dict[str, str] = {}

    resolved = resolve_cfe_root(None, environ, tmp_path)
    assert resolved.step == STEP_NOT_FOUND, (
        "test environment is not genuinely CFE-unresolvable: a "
        ".claude/scripts/conda-forge-expert/ marker was found upward from "
        f"{tmp_path} at {resolved.root} -- this whole file's premise "
        "depends on tmp_path being marker-less"
    )

    return environ, tmp_path


# --- package.build() ---------------------------------------------------------

_PEP517_RESULT = Pep517BuildResult(
    returncode=0,
    wheel_path="/proj/dist/pkg-0.1.0-py3-none-any.whl",
    sdist_path="/proj/dist/pkg-0.1.0.tar.gz",
    wheel_version="0.1.0",
    stdout="Successfully built pkg\n",
)
_PIXI_BUILD_RESULT = PixiBuildResult(
    returncode=0,
    conda_path="/proj/dist-conda/pkg-0.1.0-abc123_0.conda",
    conda_version="0.1.0",
    stdout="Building pkg\n",
)


def test_package_build_runs_normally_with_cfe_root_unresolvable(cfe_unresolvable):
    """AC1 for `package build`: `build()` never touches CFE at all -- it has
    no CFE parameter (Code Map) -- so patching `resolve_cfe_root` itself and
    asserting it is never called is the strongest available proof."""
    _, start_directory = cfe_unresolvable
    proj = start_directory / "proj"
    proj.mkdir()

    with (
        patch(
            "pyforge.mason.package.pep517.build",
            return_value=_PEP517_RESULT,
        ) as mock_pep517,
        patch(
            "pyforge.mason.package.pixi.build",
            return_value=_PIXI_BUILD_RESULT,
        ) as mock_pixi,
        patch(
            "pyforge.mason.package.resolve_cfe_root",
        ) as mock_resolve,
    ):
        result = package.build(str(proj))

    mock_pep517.assert_called_once()
    mock_pixi.assert_called_once()
    mock_resolve.assert_not_called()
    assert isinstance(result, PackageBuildResult)
    assert result.wheel_path == _PEP517_RESULT.wheel_path
    assert result.conda_path == _PIXI_BUILD_RESULT.conda_path


# --- package.ship(): every non-conda-forge target normal, conda-forge FAILED
# with the FR-5 reason specifically (AC1, AC2, AC3) -------------------------

_TWINE_UPLOAD_RESULT = TwineUploadResult(
    returncode=0,
    url="https://pypi.org/project/pkg/0.1.0/",
    stdout="View at:\n...\n",
)
_PIXI_UPLOAD_RESULT = PixiUploadResult(returncode=0, stdout="Uploaded\n")

_SHIP_CREDENTIALS = {
    "TWINE_USERNAME": "__token__",
    "TWINE_PASSWORD": "pypi-secret",
    "PREFIX_API_KEY": "acme-secret",
}
"""Credentials `ship_pypi`/`ship_channel` require BEFORE they will even call
`build()` (AD-14) -- deliberately carries no `MASON_CFE_ROOT` key, so
merging it into `cfe_unresolvable`'s empty `environ` keeps the whole
`environ` mapping genuinely CFE-unresolvable while still letting the
non-`conda-forge` targets reach their real upload path."""


def test_ship_multi_target_all_but_conda_forge_succeed_with_cfe_root_unresolvable(
    cfe_unresolvable,
):
    """AC1 (non-excepted targets behave normally), AC2 (allow-list drives
    the assertion), AC3 (the `conda-forge` target fails specifically for
    the FR-5 reason, inside the SAME multi-target invocation as the other
    two) -- all three in one call, mirroring the spec's own I/O matrix row.

    `confirm=True` (the real-ship path) and a non-blank `recipe_path` are
    both required here (spec Always boundary): `ship_conda_forge` checks
    `recipe_path` presence BEFORE resolving the CFE root, so a blank one
    would raise `ShipCondaForgeRecipeMissingError` instead -- the wrong
    error for this test's purpose -- and the dry-run (`confirm=False`) path
    with only `conda-forge` requested never calls `ship_conda_forge` at all.
    """
    environ, start_directory = cfe_unresolvable
    environ = {**environ, **_SHIP_CREDENTIALS}
    recipe_path = str(start_directory / "recipes" / "some-pkg")

    with (
        patch(
            "pyforge.mason.package.pep517.build",
            return_value=_PEP517_RESULT,
        ),
        patch(
            "pyforge.mason.package.pixi.build",
            return_value=_PIXI_BUILD_RESULT,
        ),
        patch(
            "pyforge.mason.package.pypi_index.version_exists",
            return_value=False,
        ),
        patch(
            "pyforge.mason.package.twine.upload",
            return_value=_TWINE_UPLOAD_RESULT,
        ),
        patch(
            "pyforge.mason.package.pixi.search",
            return_value=False,
        ),
        patch(
            "pyforge.mason.package.pixi.upload",
            return_value=_PIXI_UPLOAD_RESULT,
        ),
    ):
        results = package.ship(
            "pypi,channel:acme,conda-forge",
            confirm=True,
            environ=environ,
            recipe_path=recipe_path,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            start_directory=start_directory,
        )

    by_target = {r.target: r for r in results}
    assert set(by_target) == {"pypi", "channel:acme", "conda-forge"}

    cfe_unresolved_identifier = CfeUnresolvedError().identifier
    for target_name, result in by_target.items():
        if target_name in _CFE_DEPENDENT_SHIP_TARGETS:
            assert result.state is ShipState.FAILED, f"{target_name!r} (CFE-dependent) should FAIL with no CFE present"
            assert result.message is not None and cfe_unresolved_identifier in result.message, (
                f"{target_name!r} failed, but not for the FR-5 reason: {result.message!r}"
            )
        else:
            assert result.state is ShipState.TERMINAL, (
                f"{target_name!r} (not CFE-dependent) should succeed normally, got {result.state!r}: {result.message!r}"
            )
            assert result.message is None or cfe_unresolved_identifier not in result.message


# --- environment.lock() / environment.check() -------------------------------

_CONDA_LOCK_RESULT = CondaLockResult(
    returncode=0,
    lockfile_path="/proj/conda-lock.yml",
    engine_name="conda-lock",
    engine_version="4.0.2",
    stdout="",
)
_CONDA_LOCK_CHECK_RESULT = CondaLockCheckResult(
    stale=False,
    returncode=0,
    engine_name="conda-lock",
    engine_version="4.0.2",
    stdout="",
)


def test_environment_lock_runs_normally_with_cfe_root_unresolvable(cfe_unresolvable):
    """AC1 for `environment lock`: `lock()`, like `build()`, has no CFE
    parameter at all -- there is nothing CFE-shaped to force here beyond the
    shared `cfe_unresolvable` setup itself. `condalock.lock` is mocked, and
    `lock()` itself does no manifest-existence pre-validation (its own
    docstring), so the manifest path need not exist on disk."""
    _, start_directory = cfe_unresolvable
    manifest = str(start_directory / "environment.yml")
    output_path = str(start_directory / "conda-lock.yml")

    with patch(
        "pyforge.mason.environment.condalock.lock",
        return_value=_CONDA_LOCK_RESULT,
    ) as mock_lock:
        result = environment.lock([manifest], output_path)

    mock_lock.assert_called_once()
    assert isinstance(result, LockResult)
    assert result.engine_name == "conda-lock"
    assert result.returncode == 0


def test_environment_check_runs_normally_with_cfe_root_unresolvable(cfe_unresolvable):
    """AC1 for `environment check`, mirroring `lock()`'s own coverage
    above. `check()` defers lockfile-existence validation to
    `condalock.check()` itself (its own docstring), which is mocked here,
    so neither path need exist on disk."""
    _, start_directory = cfe_unresolvable
    manifest = str(start_directory / "environment.yml")
    lockfile = str(start_directory / "conda-lock.yml")

    with patch(
        "pyforge.mason.environment.condalock.check",
        return_value=_CONDA_LOCK_CHECK_RESULT,
    ) as mock_check:
        result = environment.check(lockfile, [manifest])

    mock_check.assert_called_once()
    assert isinstance(result, CheckResult)
    assert result.stale is False


# --- Module imports (AC4) ---------------------------------------------------
#
# `pyforge.mason.package`/`.environment` are already imported at this file's
# own top (module scope, collection time) -- a bare `import` statement here
# would be a `sys.modules` cache hit that re-executes nothing, proving
# nothing about the CURRENT (fixture-controlled, CFE-unresolvable) process
# state. `importlib.reload()` genuinely re-runs each module's top-level code
# while `cfe_unresolvable` has the process cwd `monkeypatch.chdir`'d to a
# marker-less `tmp_path`, so this is a real (if narrow -- AD-6 already
# forbids either module any module-level `cfe` reference) dynamic check.


def test_package_module_imports_successfully_with_no_cfe_reachable(cfe_unresolvable):
    importlib.reload(package)


def test_environment_module_imports_successfully_with_no_cfe_reachable(cfe_unresolvable):
    importlib.reload(environment)
